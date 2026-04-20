from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger, UnorderedObjectListWarning
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt 
from django.db.models import Avg, Max, Count, Q, Case, When, Value, IntegerField, Subquery, OuterRef
from django.db.models.functions import TruncDate
from django.utils.dateparse import parse_date
from django.db import transaction
from django.template.loader import render_to_string
from django.conf import settings
import os, json
from django.utils import timezone
from django.core.cache import cache
from functools import wraps

import warnings
from .forms import UserForm, ProfileForm
from .models import MineMap, UserProfile, InfrastructureDevice, Employee, MinerDevice, SecurityAlert, TelemetryLog, FirmwareUpdate, OTALog

# --- ДОПОМІЖНА ФУНКЦІЯ ---

# Секретний ключ для API (завантажується з .env, інакше використовується дефолтний)
ESP32_API_KEY = os.environ.get("ESP32_API_KEY", "SecretMineKey2026")

def api_key_required(view_func):
    """Декоратор для перевірки API-ключа у запитах від ESP32 та інших зовнішніх систем."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Шукаємо ключ у заголовку X-API-Key або в параметрах URL ?api_key=...
        api_key = request.headers.get('X-API-Key') or request.GET.get('api_key')
        if api_key != ESP32_API_KEY:
            return JsonResponse({'error': 'Unauthorized. Invalid API Key.'}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def get_active_map():
    """Повертає актуальну карту шахти з кешуванням."""
    cache_key = 'active_mine_map'
    map_obj = cache.get(cache_key)
    if not map_obj:
        map_obj = MineMap.objects.filter(name="Основний горизонт").first() or MineMap.objects.order_by('-updated_at').first()
        if map_obj:
            cache.set(cache_key, map_obj, 3600)  # Кешуємо на 1 годину
    return map_obj

def get_zone_microclimate():
    """Обчислює актуальний мікроклімат, згрупований по локаціях (штреках) за останні 5 хв."""
    recent_time = timezone.now() - timezone.timedelta(minutes=5)
    # Отримуємо тільки НАЙСВІЖІШИЙ запис від КОЖНОГО пристрою за останні 5 хв
    latest_logs = TelemetryLog.objects.filter(
        timestamp__gte=recent_time
    ).order_by('device_id', '-timestamp').distinct('device_id').select_related('device', 'connected_repeater', 'connected_repeater__map_location')
    
    zones = {}
    for log in latest_logs:
        loc_name = log.connected_repeater.location_in_mine if log.connected_repeater else "Невідомо"
        if loc_name not in zones:
            zones[loc_name] = {'temp': [], 'hum': [], 'gas': [], 'people_count': 0, 'power_loss': False}
        if log.temperature is not None: zones[loc_name]['temp'].append(log.temperature)
        if log.humidity is not None: zones[loc_name]['hum'].append(log.humidity)
        zones[loc_name]['gas'].append(log.gas_level)
        
        # 1. Рахуємо людей (коногонки, прив'язані до працівника)
        if not log.device.is_static and log.device.assigned_to_id:
            zones[loc_name]['people_count'] += 1
            
        # 2. Перевіряємо живлення 220V стаціонарних датчиків (якщо заряд впав нижче 99%)
        if log.device.is_static and log.battery_level < 99:
            zones[loc_name]['power_loss'] = True
            
    result = []
    for loc, data in zones.items():
        result.append({
            'location': loc,
            'avg_temp': round(sum(data['temp'])/len(data['temp']), 1) if data['temp'] else 0.0,
            'avg_hum': round(sum(data['hum'])/len(data['hum']), 1) if data['hum'] else 0.0,
            'max_gas': round(max(data['gas']), 1) if data['gas'] else 0.0,
            'people_count': data['people_count'],
            'power_loss': data['power_loss']
        })
    # Сортуємо: спочатку найбільш загазовані та проблемні штреки
    return sorted(result, key=lambda x: x['max_gas'], reverse=True)

# --- ОСНОВНІ СТОРІНКИ ---


@login_required
def diploma_home(request):
    """Головна панель управління."""
    online_staff = Employee.objects.exclude(safety_status='OFF_SHIFT')

    # Беремо ID останніх 50 записів телеметрії
    recent_log_ids = TelemetryLog.objects.order_by('-timestamp').values_list('id', flat=True)[:50]
    
    # Рахуємо: СЕРЕДНЄ для температури/вологості, МАКСИМАЛЬНЕ для газу
    stats = TelemetryLog.objects.filter(id__in=recent_log_ids).aggregate(
        avg_temp=Avg('temperature'),
        avg_hum=Avg('humidity'),
        max_gas=Max('gas_level')
    )
    
    mine_map = get_active_map()

    active_alerts_query = SecurityAlert.objects.filter(is_resolved=False)
    alerts_count = active_alerts_query.count()
    
    latest_log_subquery = TelemetryLog.objects.filter(
        device__assigned_to=OuterRef('pk')
    ).order_by('-timestamp').values('id')[:1]

    all_recent_staff = list(online_staff.select_related('device').annotate(
        latest_log_id=Subquery(latest_log_subquery),
        status_order=Case(
            When(safety_status='SOS', then=Value(1)),
            When(safety_status='WARNING', then=Value(2)),
            default=Value(3),
            output_field=IntegerField()
        )
    ).order_by('status_order', '-last_update'))
    
    problem_staff = [emp for emp in all_recent_staff if emp.safety_status in ['SOS', 'WARNING']]
    recent_staff_qs = problem_staff if len(problem_staff) >= 4 else all_recent_staff[:4]

    log_ids = [emp.latest_log_id for emp in recent_staff_qs if emp.latest_log_id]
    logs_dict = {log.device_id: log for log in TelemetryLog.objects.filter(id__in=log_ids).select_related('connected_repeater')}

    recent_time = timezone.now() - timezone.timedelta(minutes=5)
    for emp in recent_staff_qs:
        emp.latest_location = None
        if getattr(emp, 'device', None) and emp.device.is_active:
            last_log = logs_dict.get(emp.device.id)
            if last_log and last_log.connected_repeater and last_log.timestamp >= recent_time:
                emp.latest_location = last_log.connected_repeater.uid

    context = {
        'online_count': online_staff.count(),
        'warning_count': alerts_count,
        'zone_microclimate': get_zone_microclimate(),
        'recent_staff': recent_staff_qs,
        'active_alerts': active_alerts_query.select_related('employee', 'device', 'connected_repeater').order_by('-created_at')[:5],
        'critical_alerts_count': active_alerts_query.exclude(status='WARNING').count(),
        'avg_temp': stats['avg_temp'] if stats['avg_temp'] is not None else 0.0,
        'avg_hum': stats['avg_hum'] if stats['avg_hum'] is not None else 0.0,
        'gas_level': stats['max_gas'] if stats['max_gas'] is not None else 0,
        'map_data': mine_map.map_data if mine_map else {},
    }
    return render(request, 'diploma/diploma_home.html', context)


@login_required
def personnel_list(request):
    """Список персоналу (тепер завантажується через API)."""
    return render(request, 'diploma/personnel.html')


@login_required
def equipment_list(request):
    """Парк обладнання (тепер завантажується через API)."""
    lamps_count = MinerDevice.objects.filter(is_static=False).count()
    sensors_count = MinerDevice.objects.filter(is_static=True).count()
    repeaters_count = InfrastructureDevice.objects.count()
    
    return render(request, 'diploma/equipment.html', {
        'lamps_count': lamps_count,
        'sensors_count': sensors_count,
        'repeaters_count': repeaters_count,
    })


@login_required
def reports_view(request):
    """Сторінка звітів та список доступних архівів телеметрії."""
    archives = []
    
    # Лише суперкористувачі можуть бачити список архівів
    if request.user.is_superuser:
        archive_dir = os.path.join(settings.BASE_DIR, 'archives', 'telemetry')
        
        if os.path.exists(archive_dir):
            for file in os.listdir(archive_dir):
                if file.endswith('.csv.gz'):
                    file_path = os.path.join(archive_dir, file)
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    mtime = timezone.datetime.fromtimestamp(os.path.getmtime(file_path))
                    archives.append({
                        'name': file,
                        'size_mb': round(size_mb, 2),
                        'date': mtime.strftime('%Y-%m-%d %H:%M')
                    })
                    
        # Сортуємо від найновіших до найстаріших
        archives.sort(key=lambda x: x['name'], reverse=True)
    
    return render(request, 'diploma/reports.html', {'archives': archives})

@login_required
def download_archive(request, filename):
    """Функція для безпечного завантаження архіву."""
    if not request.user.is_superuser:
        return HttpResponse("Доступ заборонено. Тільки для адміністраторів.", status=403)
        
    # Захист від Path Traversal (щоб хакер не міг завантажити системні файли сервера)
    if not filename.endswith('.csv.gz') or '/' in filename or '\\' in filename:
        return HttpResponse("Недійсний файл", status=400)
        
    file_path = os.path.join(settings.BASE_DIR, 'archives', 'telemetry', filename)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/gzip')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
    raise Http404("Файл не знайдено")

@login_required
def mine_map(request):
    mine_map = get_active_map()
    return render(request, 'diploma/mine_map.html', {
        'map_data': mine_map.map_data if mine_map else {},
        'map_name': mine_map.name if mine_map else "Немає даних"
    })

# --- УПРАВЛІННЯ ІНЦИДЕНТАМИ ---


@login_required
def alert_detail(request, alert_id):
    """Детальна сторінка інциденту з панеллю управління."""
    alert = get_object_or_404(SecurityAlert, id=alert_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        alert.rescue_notes = request.POST.get('rescue_notes', '')

        if new_status:
            alert.status = new_status
            if new_status == 'RESOLVED':
                alert.is_resolved, alert.resolved_at, alert.resolved_by = True, timezone.now(), request.user
                emp = alert.employee
                if emp:
                    # Скидаємо візуальний статус працівника ТІЛЬКИ якщо більше немає активних тривог
                    if not SecurityAlert.objects.filter(employee=emp, is_resolved=False).exclude(id=alert.id).exists():
                        emp.safety_status = 'OK'
                        emp.save()
            else:
                alert.is_resolved = False

        alert.save()
        messages.success(
            request, f"Статус оновлено: {alert.get_status_display()}")
        return redirect('alert_detail', alert_id=alert.id)

    latest_telemetry = TelemetryLog.objects.filter(
        device=alert.device).order_by('-timestamp').first()
        
    next_alert = SecurityAlert.objects.filter(is_resolved=False).exclude(id=alert.id).order_by('created_at').first()
    
    return render(request, 'diploma/alert_detail.html', {'alert': alert, 'telemetry': latest_telemetry, 'next_alert': next_alert})

# --- API ЕНДПОІНТИ (ДЛЯ JS ТА ЗОВНІШНІХ ПРОГРАМ) ---


def dashboard_stats_api(request):
    """API для автоматичного оновлення показників мікроклімату на головній сторінці."""
    # --- ПЕРЕВІРКА НА ВТРАТУ ЗВ'ЯЗКУ (ОФЛАЙН) ---
    three_mins_ago = timezone.now() - timezone.timedelta(minutes=3)
    latest_log_subquery = TelemetryLog.objects.filter(
        device__assigned_to=OuterRef('pk')
    ).order_by('-timestamp')
    
    latest_time_subquery = latest_log_subquery.values('timestamp')[:1]
    latest_id_subquery = latest_log_subquery.values('id')[:1]
    
    offline_emps = list(Employee.objects.exclude(safety_status='OFF_SHIFT').filter(
        device__isnull=False
    ).select_related('device').annotate(
        last_seen=Subquery(latest_time_subquery),
        latest_log_id=Subquery(latest_id_subquery)
    ).filter(last_seen__lt=three_mins_ago))
    
    if offline_emps:
        offline_log_ids = [emp.latest_log_id for emp in offline_emps if emp.latest_log_id]
        offline_logs_dict = {log.device_id: log for log in TelemetryLog.objects.filter(id__in=offline_log_ids).select_related('connected_repeater')}
        
        from collections import defaultdict
        newly_offline = []
        
        for emp in offline_emps:
            last_seen_time = emp.last_seen or (timezone.now() - timezone.timedelta(days=1))
            last_log = offline_logs_dict.get(emp.device.id)
            rep = last_log.connected_repeater if last_log else None
            
            has_offline_alert = SecurityAlert.objects.filter(employee=emp, reason__icontains="Втрата зв'язку", created_at__gte=last_seen_time).exists()
            has_infra_alert = SecurityAlert.objects.filter(connected_repeater=rep, reason__icontains="Аварія інфраструктури", is_resolved=False).exists() if rep else False
            
            if not has_offline_alert and not has_infra_alert:
                newly_offline.append((emp, last_log, rep))
                
        repeater_groups = defaultdict(list)
        for emp, last_log, rep in newly_offline:
            repeater_groups[rep].append((emp, last_log))
            
        for rep, emps_data in repeater_groups.items():
            if rep and rep.uid == 'AP-SURFACE':
                for emp, _ in emps_data:
                    has_critical = SecurityAlert.objects.filter(employee=emp, is_resolved=False).exclude(status='WARNING').exists()
                    if not has_critical:
                        emp.safety_status = 'OFF_SHIFT'
                        emp.save()
                        if getattr(emp, 'device', None):
                            emp.device.is_active = False
                            emp.device.save()
                continue

            # Рахуємо ВСІХ офлайн-працівників на цьому репітері, а не тільки щойно відключених
            all_offline_at_this_repeater = [
                e for e in offline_emps 
                if offline_logs_dict.get(e.device.id) and offline_logs_dict.get(e.device.id).connected_repeater == rep
            ]
            num_total_offline = len(all_offline_at_this_repeater)
            
            infra_alert_created = False
            # Умова спрацьовує, якщо ЗАГАЛЬНА кількість офлайн-працівників на репітері >= 3
            if rep and num_total_offline >= 3:
                # Перевіряємо, чи немає вже активної групової тривоги для цього репітера
                has_infra_alert = SecurityAlert.objects.filter(connected_repeater=rep, reason__icontains="Аварія інфраструктури", is_resolved=False).exists()
                if not has_infra_alert:
                    first_emp, _ = emps_data[0]
                    reason = f"🚨 Аварія інфраструктури! Знеструмлено репітер {rep.uid}. Втрачено зв'язок з {num_total_offline} працівниками."
                    SecurityAlert.objects.create(
                        employee=None, device=first_emp.device, connected_repeater=rep,
                        reason=reason, status='NEW'
                    )
                    
                    # Очищення: знаходимо та закриваємо індивідуальні тривоги, що могли бути створені хвилину тому
                    one_minute_ago = timezone.now() - timezone.timedelta(minutes=1)
                    employee_ids_in_group = [e.id for e in all_offline_at_this_repeater]
                    SecurityAlert.objects.filter(
                        employee_id__in=employee_ids_in_group,
                        reason__icontains="Втрата зв'язку",
                        created_at__gte=one_minute_ago,
                        is_resolved=False
                    ).update(
                        status='RESOLVED', is_resolved=True, resolved_at=timezone.now(),
                        rescue_notes=f"Перевизначено груповою тривогою по репітеру {rep.uid}."
                    )
                
                infra_alert_created = True

            # Створюємо індивідуальні тривоги тільки якщо групова не була створена
            for emp, last_log in emps_data:
                if not infra_alert_created:
                    bat_info = ""
                    if last_log and last_log.battery_level <= 15:
                        bat_info = f" (Останній заряд: {last_log.battery_level}%, можливо розрядився)"
                        
                    SecurityAlert.objects.create(
                        employee=emp, device=emp.device, connected_repeater=rep,
                        reason=f"Втрата зв'язку (>3 хв). Останній репітер: {rep.uid if rep else 'Невідомо'}{bat_info}", status='WARNING'
                    )
                
                if emp.safety_status == 'OK':
                    emp.safety_status = 'WARNING'
                    emp.save()

    recent_log_ids = TelemetryLog.objects.order_by('-timestamp').values_list('id', flat=True)[:50]
    stats = TelemetryLog.objects.filter(id__in=recent_log_ids).aggregate(
        avg_temp=Avg('temperature'),
        avg_hum=Avg('humidity'),
        max_gas=Max('gas_level')
    )
    
    online_count = Employee.objects.exclude(safety_status='OFF_SHIFT').count()
    warning_count = SecurityAlert.objects.filter(is_resolved=False).count()
    new_alerts_count = SecurityAlert.objects.filter(status='NEW').count()
    
    # --- НОВЕ: Рендеримо HTML для списку сповіщень ---
    active_alerts = SecurityAlert.objects.filter(is_resolved=False).select_related('employee', 'device', 'connected_repeater').order_by('-created_at')[:5]
    alerts_html = render_to_string('diploma/_alert_list.html', {
        'active_alerts': active_alerts,
        'request': request  # Передаємо request для роботи `url` тега
    })

    # Збираємо останніх активних працівників для віджета "Персонал у шахті"
    all_recent_staff = list(Employee.objects.exclude(safety_status='OFF_SHIFT').annotate(
        latest_log_id=Subquery(latest_id_subquery),
        status_order=Case(
            When(safety_status='SOS', then=Value(1)),
            When(safety_status='WARNING', then=Value(2)),
            default=Value(3),
            output_field=IntegerField()
        )
    ).select_related('device').order_by('status_order', '-last_update'))
    
    problem_staff = [emp for emp in all_recent_staff if emp.safety_status in ['SOS', 'WARNING']]
    if len(problem_staff) >= 4:
        recent_staff = problem_staff
    else:
        recent_staff = all_recent_staff[:4]
    
    recent_staff_log_ids = [emp.latest_log_id for emp in recent_staff if emp.latest_log_id]
    recent_logs_dict = {log.device_id: log for log in TelemetryLog.objects.filter(id__in=recent_staff_log_ids).select_related('connected_repeater')}

    recent_staff_data = []
    recent_time = timezone.now() - timezone.timedelta(minutes=5)
    for emp in recent_staff:
        location_uid = None
        if getattr(emp, 'device', None) and emp.device.is_active:
            last_log = recent_logs_dict.get(emp.device.id)
            if last_log and last_log.connected_repeater and last_log.timestamp >= recent_time:
                location_uid = last_log.connected_repeater.uid
                
        recent_staff_data.append({
            'first_name': emp.first_name,
            'last_name': emp.last_name,
            'position': emp.get_position_display(),
            'status': emp.safety_status,
            'photo_url': emp.photo.url if emp.photo else None,
            'location': location_uid
        })

    # --- НОВЕ: Сповіщення про відновлення зв'язку ---
    recently_resolved_time = timezone.now() - timezone.timedelta(seconds=7)
    reconnected_alerts = SecurityAlert.objects.filter(
        reason__icontains="Втрата зв'язку",
        status='RESOLVED',
        resolved_at__gte=recently_resolved_time
    ).select_related('employee')
    
    reconnected_names = list(set([f"{a.employee.first_name} {a.employee.last_name}" for a in reconnected_alerts if a.employee]))

    # --- НОВЕ: Сповіщення про відновлення живлення 220V ---
    power_restored_alerts = SecurityAlert.objects.filter(
        reason__icontains="Аварія живлення",
        status='RESOLVED',
        resolved_at__gte=recently_resolved_time
    ).select_related('connected_repeater')
    
    power_restored_zones = list(set([a.connected_repeater.location_in_mine if a.connected_repeater else "Невідомо" for a in power_restored_alerts]))

    # --- НОВЕ: Сповіщення про відновлення інфраструктури ---
    infra_restored_alerts = SecurityAlert.objects.filter(
        reason__icontains="Аварія інфраструктури",
        status='RESOLVED',
        resolved_at__gte=recently_resolved_time
    ).select_related('connected_repeater')
    
    infra_restored_zones = list(set([a.connected_repeater.uid for a in infra_restored_alerts if a.connected_repeater]))

    return JsonResponse({
        'avg_temp': stats['avg_temp'] if stats['avg_temp'] is not None else 0.0,
        'avg_hum': stats['avg_hum'] if stats['avg_hum'] is not None else 0.0,
        'gas_level': stats['max_gas'] if stats['max_gas'] is not None else 0,
        'online_count': online_count,
        'warning_count': warning_count,
        'new_alerts_count': new_alerts_count,
        'zones_data': get_zone_microclimate(),
        'alerts_html': alerts_html, # Додаємо HTML до відповіді
        'recent_staff': recent_staff_data,
        'reconnected_names': reconnected_names,
        'power_restored_zones': power_restored_zones,
        'infra_restored_zones': infra_restored_zones,
    })

@login_required
def equipment_list_api(request):
    """API для динамічного завантаження, пошуку та сортування обладнання."""
    
    # 1. Отримуємо параметри
    tab = request.GET.get('tab', 'lamps')
    search_query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'status')
    sort_dir = request.GET.get('dir', 'desc')
    page_number = request.GET.get('page', 1)
    
    qs = None
    template_name = ''
    
    # Ігноруємо попередження про пагінацію для невпорядкованих запитів, оскільки ми завжди задаємо порядок
    warnings.filterwarnings('ignore', category=UnorderedObjectListWarning)

    # 2. Вибираємо запит в залежності від вкладки
    if tab == 'lamps':
        latest_log_battery = TelemetryLog.objects.filter(device=OuterRef('pk')).order_by('-timestamp').values('battery_level')[:1]
        qs = MinerDevice.objects.filter(is_static=False).select_related('assigned_to').annotate(
            latest_battery=Subquery(latest_log_battery)
        )
        template_name = 'diploma/_equipment_lamps_rows.html'
        
        if search_query:
            qs = qs.filter(
                Q(inventory_number__icontains=search_query) | Q(mac_address__icontains=search_query) |
                Q(assigned_to__last_name__icontains=search_query) | Q(assigned_to__first_name__icontains=search_query) |
                Q(assigned_to__badge_number__icontains=search_query)
            )
            
        order_field = '-is_active'
        if sort_by == 'battery': order_field = 'latest_battery'
        elif sort_by == 'firmware': order_field = 'firmware_version'
        elif sort_by == 'status': order_field = 'is_active'
        
        order_prefix = '-' if sort_dir == 'desc' else ''
        qs = qs.order_by(f'{order_prefix}{order_field}', 'inventory_number')

    elif tab == 'sensors':
        qs = MinerDevice.objects.filter(is_static=True)
        template_name = 'diploma/_equipment_sensors_rows.html'
        
        if search_query:
            qs = qs.filter(Q(inventory_number__icontains=search_query) | Q(mac_address__icontains=search_query))
            
        order_field = '-is_active'
        if sort_by == 'firmware': order_field = 'firmware_version'
        elif sort_by == 'status': order_field = 'is_active'

        order_prefix = '-' if sort_dir == 'desc' else ''
        qs = qs.order_by(f'{order_prefix}{order_field}', 'inventory_number')

    elif tab == 'repeaters':
        recent_time = timezone.now() - timezone.timedelta(minutes=5)
        client_subquery = TelemetryLog.objects.filter(
            connected_repeater=OuterRef('pk'),
            timestamp__gte=recent_time,
            device__is_static=False
        ).order_by().values('connected_repeater').annotate(c=Count('device_id', distinct=True)).values('c')

        qs = InfrastructureDevice.objects.select_related('map_location').annotate(
            is_main=Case(When(uid='AP-SURFACE', then=Value(0)), default=Value(1), output_field=IntegerField()),
            clients_count=Subquery(client_subquery, output_field=IntegerField())
        )
        template_name = 'diploma/_equipment_repeaters_rows.html'
        
        if search_query:
            qs = qs.filter(Q(uid__icontains=search_query) | Q(wifi_bssid__icontains=search_query))
        
        order_prefix = '-' if sort_dir == 'desc' else ''
        if sort_by == 'clients':
            qs = qs.order_by(f'{order_prefix}clients_count', 'uid')
        elif sort_by == 'status':
            qs = qs.order_by(f'{order_prefix}is_active', 'uid')
        else: # Сортування за замовчуванням
            qs = qs.order_by('is_main', '-clients_count')

    if qs is None:
        return JsonResponse({'error': 'Invalid tab'}, status=400)

    # 3. Пагінація
    paginator = Paginator(qs, 15)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    # 4. Додаткова обробка телеметрії для поточної сторінки
    context_data = {'items': page_obj.object_list}
    
    if tab in ['lamps', 'sensors']:
        latest_log_subquery = TelemetryLog.objects.filter(device=OuterRef('pk')).order_by('-timestamp').values('id')[:1]
        items_on_page = list(page_obj.object_list.annotate(latest_log_id=Subquery(latest_log_subquery)))
        log_ids = [d.latest_log_id for d in items_on_page if getattr(d, 'latest_log_id', None)]
        logs_dict = {log.device_id: log for log in TelemetryLog.objects.filter(id__in=log_ids)}
        for device in items_on_page:
            device.latest_log = logs_dict.get(device.id)
        context_data['items'] = items_on_page
        
    elif tab == 'repeaters':
        # Отримуємо список клієнтів для тултіпів
        repeater_ids_on_page = [r.id for r in page_obj.object_list]
        recent_time = timezone.now() - timezone.timedelta(minutes=5)
        
        latest_logs = TelemetryLog.objects.filter(
            connected_repeater_id__in=repeater_ids_on_page,
            timestamp__gte=recent_time,
            device__is_static=False
        ).order_by('device_id', '-timestamp').distinct('device_id').select_related('device__assigned_to')

        client_lists = {rep_id: [] for rep_id in repeater_ids_on_page}
        for log in latest_logs:
            device = log.device
            name = f"{device.assigned_to.last_name} {device.assigned_to.first_name[0]}." if device.assigned_to else device.inventory_number
            client_lists[log.connected_repeater_id].append(name)

        for rep in page_obj.object_list:
            rep.clients_list_str = "\n".join(client_lists.get(rep.id, []))

    # 5. Рендеримо HTML та повертаємо JSON
    html = render_to_string(template_name, context_data)
    
    return JsonResponse({
        'html': html, 'total_pages': paginator.num_pages, 'current_page': page_obj.number,
        'total_results': paginator.count, 'has_next': page_obj.has_next()
    })

@login_required
def personnel_list_api(request):
    """API для динамічного завантаження, пошуку та сортування персоналу."""
    
    # 1. Отримуємо параметри з GET-запиту
    search_query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'status') # 'status' or 'name'
    
    # 2. Базовий запит
    base_qs = Employee.objects.all_with_device_status()

    # 3. Застосовуємо пошук
    if search_query:
        base_qs = base_qs.filter(
            Q(last_name__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(badge_number__icontains=search_query) |
            Q(position__icontains=search_query)
        )

    # 4. Застосовуємо сортування
    if sort_by == 'name':
        # Сортування за прізвищем, потім за ім'ям
        employees_qs = base_qs.order_by('last_name', 'first_name')
    else: # 'status' or default
        # Сортування за статусом (активні вгорі), потім за прізвищем
        employees_qs = base_qs.annotate(
            status_order=Case(
                When(device__is_active=True, then=Value(1)),
                When(device__is_active=False, then=Value(2)),
                default=Value(3),
                output_field=IntegerField()
            )
        ).order_by('status_order', 'last_name', 'first_name')

    # 5. Пагінація
    paginator = Paginator(employees_qs, 12) # 12 карток на сторінку
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        # Якщо сторінка не є числом або порожня, повертаємо першу
        page_obj = paginator.page(1)

    # 6. Оптимізація для отримання локації (як було раніше)
    latest_log_subquery = TelemetryLog.objects.filter(device__assigned_to=OuterRef('pk')).order_by('-timestamp').values('id')[:1]
    employees_on_page = list(page_obj.object_list.annotate(latest_log_id=Subquery(latest_log_subquery)))
    log_ids = [emp.latest_log_id for emp in employees_on_page if getattr(emp, 'latest_log_id', None)]
    logs_dict = {log.device_id: log for log in TelemetryLog.objects.filter(id__in=log_ids).select_related('connected_repeater')}
    recent_time = timezone.now() - timezone.timedelta(minutes=5)
    for emp in employees_on_page:
        emp.latest_location = None
        if hasattr(emp, 'device') and emp.device.is_active:
            last_log = logs_dict.get(emp.device.id)
            if last_log and last_log.connected_repeater and last_log.timestamp >= recent_time:
                emp.latest_location = last_log.connected_repeater.uid
    
    html = render_to_string('diploma/_personnel_cards.html', {'employees': employees_on_page, 'request': request})
    return JsonResponse({'html': html, 'has_next': page_obj.has_next(), 'total_pages': paginator.num_pages, 'current_page': page_obj.number, 'total_results': paginator.count})

def alert_telemetry_api(request, alert_id):
    """Повертає свіжу телеметрію для конкретної тривоги."""
    alert = get_object_or_404(SecurityAlert, id=alert_id)
    latest = TelemetryLog.objects.filter(
        device=alert.device).order_by('-timestamp').first()
    if not latest:
        return JsonResponse({'status': 'no_data'})
    return JsonResponse({
        'status': 'ok', 'gas': latest.gas_level, 'temp': latest.temperature,
        'moving': latest.is_moving, 'rssi': latest.wifi_signal_strength,
        'timestamp': latest.timestamp.strftime('%H:%M:%S'),
        'repeater': latest.connected_repeater.uid if latest.connected_repeater else "Втрачено"
    })


@login_required
def reports_data_api(request):
    """API для генерації даних для сторінки звітів (графіки та таблиця)."""
    report_type = request.GET.get('type', 'incidents')
    start_date = parse_date(request.GET.get('start_date', ''))
    end_date = parse_date(request.GET.get('end_date', ''))
    
    if not start_date or not end_date:
        return JsonResponse({'error': 'Не вказані дати'}, status=400)

    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
    per_page = 50
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    # --- ЗВІТ ПО ІНЦИДЕНТАХ (SOS) ---
    if report_type == 'incidents':
        # Фільтруємо реальні тривоги з БД за обраний період
        alerts = SecurityAlert.objects.filter(
            created_at__date__gte=start_date, 
            created_at__date__lte=end_date
        )
        
        # 1. Дані для лінійного графіка (згруповані по днях)
        alerts_by_date = alerts.annotate(date=TruncDate('created_at')).values('date').annotate(count=Count('id')).order_by('date')
        main_labels = [item['date'].strftime('%d.%m') for item in alerts_by_date]
        main_values = [item['count'] for item in alerts_by_date]
        
        # 2. Дані для кругового графіка (Розподіл причин тривог)
        sos_count = alerts.filter(reason__icontains='SOS').count()
        gas_count = alerts.filter(Q(reason__icontains='CO') | Q(reason__icontains='CH4')).count()
        other_count = alerts.exclude(reason__icontains='SOS').exclude(reason__icontains='CO').exclude(reason__icontains='CH4').count()
        
        doughnut_labels = ['Кнопка SOS', 'Газ (Метан)', 'Інше']
        doughnut_values = [sos_count, gas_count, other_count]
        doughnut_colors = ['#ff4444', '#ff9800', '#ffd700']
        
        alerts_qs = alerts.order_by('-created_at')
        total_records = alerts_qs.count()
        total_pages = (total_records + per_page - 1) // per_page

        # 3. Рядки для таблиці
        table_rows = []
        for alert in alerts_qs[start_idx:end_idx]:
            status_classes = {
                'RESOLVED': ('bg-success', 'Вирішено', 'text-muted'), 
                'IN_PROGRESS': ('bg-warning text-dark', 'В роботі', 'text-warning'),
                'WARNING': ('bg-info text-dark', 'Попередження', 'text-info')
            }
            s_badge, s_text, e_class = status_classes.get(alert.status, ('bg-danger', 'Нова', 'text-danger'))
                
            # Відображення локації з репітера, якщо він є
            location = alert.connected_repeater.uid if alert.connected_repeater else (alert.location_label or 'Невідомо')
            
            # Додаємо коментарі диспетчера та хто закрив тривогу
            notes_html = ""
            if alert.rescue_notes or alert.resolved_by:
                dispatcher_name = alert.resolved_by.get_full_name() or alert.resolved_by.username if alert.resolved_by else ""
                notes_text = f"Заходи: {alert.rescue_notes}" if alert.rescue_notes else ""
                resolver_text = f"Диспетчер: {dispatcher_name}" if dispatcher_name else ""
                combined_notes = " | ".join(filter(None, [resolver_text, notes_text]))
                if combined_notes:
                    notes_html = f'<div class="dispatcher-notes"><i class="fas fa-comment-dots"></i> {combined_notes}</div>'

            table_rows.append({
                'date': alert.created_at.strftime('%Y-%m-%d %H:%M'),
                'event_class': e_class,
                'event_text': f'<i class="fas fa-exclamation-triangle"></i> {alert.reason}{notes_html}',
                'location': location,
                'person': f"{alert.employee.last_name} {alert.employee.first_name[0]}. ({alert.device.inventory_number})" if alert.employee and alert.device else '---',
                'status_html': f'<span class="badge {s_badge}">{s_text}</span>'
            })
            
        return JsonResponse({
            'chart_main': {'labels': main_labels, 'values': main_values},
            'chart_doughnut': {'labels': doughnut_labels, 'values': doughnut_values, 'colors': doughnut_colors},
            'table_rows': table_rows,
            'pagination': {'total': total_records, 'pages': total_pages, 'current': page, 'per_page': per_page}
        })
        
    # --- ЗВІТ ПО ТЕЛЕМЕТРІЇ (ГАЗ ТА МІКРОКЛІМАТ) ---
    elif report_type == 'telemetry':
        # Фільтруємо логі телеметрії за обраний період
        logs = TelemetryLog.objects.filter(
            timestamp__date__gte=start_date, 
            timestamp__date__lte=end_date
        )
        
        # 1. Дані для лінійного графіка (Максимальний рівень газу по днях)
        logs_by_date = logs.annotate(date=TruncDate('timestamp')).values('date').annotate(max_gas=Max('gas_level')).order_by('date')
        main_labels = [item['date'].strftime('%d.%m') for item in logs_by_date]
        main_values = [item['max_gas'] for item in logs_by_date]
        
        # 2. Дані для кругового графіка (Розподіл показників газу за рівнем небезпеки)
        safe_count = logs.filter(gas_level__lt=10).count()
        warning_count = logs.filter(gas_level__gte=10, gas_level__lt=50).count()
        danger_count = logs.filter(gas_level__gte=50).count()
        
        doughnut_labels = ['Норма (<10 % LEL)', 'Увага (10-50 % LEL)', 'Небезпека (>50 % LEL)']
        doughnut_values = [safe_count, warning_count, danger_count]
        doughnut_colors = ['#00c851', '#ff9800', '#ff4444']
        
        logs_qs = logs.order_by('-gas_level', '-timestamp')
        total_records = logs_qs.count()
        total_pages = (total_records + per_page - 1) // per_page

        # 3. Рядки для таблиці (Топ-100 записів з найвищим показником газу)
        table_rows = []
        for log in logs_qs[start_idx:end_idx]:
            if log.gas_level >= 50:
                s_badge, s_text, e_class = 'bg-danger', 'Евакуація', 'text-danger'
            elif log.gas_level > 17:
                s_badge, s_text, e_class = 'bg-warning text-dark', 'Перевищення', 'text-warning'
            else:
                s_badge, s_text, e_class = 'bg-success', 'Норма', 'text-muted'
                
            person_info = f"{log.device.assigned_to.last_name} {log.device.assigned_to.first_name[0]}. ({log.device.inventory_number})" if log.device.assigned_to else f"Датчик ({log.device.inventory_number})"
            location = log.connected_repeater.uid if log.connected_repeater else 'Невідомо'
                
            table_rows.append({
                'date': log.timestamp.strftime('%Y-%m-%d %H:%M'),
                'event_class': e_class,
                'event_text': f'<i class="fas fa-fire"></i> CH4: {log.gas_level} % LEL | Темп: {log.temperature}°C',
                'location': location,
                'person': person_info,
                'status_html': f'<span class="badge {s_badge}">{s_text}</span>'
            })
            
        return JsonResponse({
            'chart_main': {'labels': main_labels, 'values': main_values},
            'chart_doughnut': {'labels': doughnut_labels, 'values': doughnut_values, 'colors': doughnut_colors},
            'table_rows': table_rows,
            'pagination': {'total': total_records, 'pages': total_pages, 'current': page, 'per_page': per_page}
        })

    # --- ЗВІТ ПО ОБЛАДНАННЮ (БАТАРЕЯ ТА МЕРЕЖА) ---
    elif report_type == 'equipment':
        logs = TelemetryLog.objects.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
        
        # 1. Графік: Кількість подій низького заряду (<20%) по днях
        low_bat_logs = logs.filter(battery_level__lt=20).annotate(date=TruncDate('timestamp')).values('date').annotate(count=Count('id')).order_by('date')
        main_labels = [item['date'].strftime('%d.%m') for item in low_bat_logs]
        main_values = [item['count'] for item in low_bat_logs]
        
        # 2. Круговий графік: Розподіл типів обладнання в системі
        doughnut_labels = ['Коногонки', 'Стаціонарні датчики', 'Репітери (Мережа)']
        doughnut_values = [
            MinerDevice.objects.filter(is_static=False).count(),
            MinerDevice.objects.filter(is_static=True).count(),
            InfrastructureDevice.objects.count()
        ]
        doughnut_colors = ['#4dabf7', '#00c851', '#ffd700']
        
        logs_qs = logs.order_by('battery_level', '-timestamp')
        total_records = logs_qs.count()
        total_pages = (total_records + per_page - 1) // per_page

        # 3. Таблиця: Топ-100 записів із найнижчим зарядом або поганим сигналом
        table_rows = []
        for log in logs_qs[start_idx:end_idx]:
            s_badge = 'bg-danger' if log.battery_level < 20 else ('bg-warning text-dark' if log.battery_level < 50 else 'bg-success')
            e_class = 'text-danger' if log.battery_level < 20 else 'text-muted'
            table_rows.append({
                'date': log.timestamp.strftime('%Y-%m-%d %H:%M'),
                'event_class': e_class,
                'event_text': f'<i class="fas fa-battery-quarter"></i> Заряд: {log.battery_level}% | Сигнал: {log.wifi_signal_strength} dBm',
                'location': log.connected_repeater.uid if log.connected_repeater else 'Зв\'язок втрачено',
                'person': f"{log.device.inventory_number} [{log.device.mac_address}]",
                'status_html': f'<span class="badge {s_badge}">{log.battery_level}%</span>'
            })
            
        return JsonResponse({
            'chart_main': {'labels': main_labels, 'values': main_values}, 
            'chart_doughnut': {'labels': doughnut_labels, 'values': doughnut_values, 'colors': doughnut_colors}, 
            'table_rows': table_rows,
            'pagination': {'total': total_records, 'pages': total_pages, 'current': page, 'per_page': per_page}
        })

    # --- ЗВІТ ПО ПЕРСОНАЛУ ---
    elif report_type == 'personnel':
        logs = TelemetryLog.objects.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date, device__is_static=False)
        
        # 1. Графік: Кількість унікальних активних працівників по днях
        active_by_date = logs.annotate(date=TruncDate('timestamp')).values('date').annotate(emp_count=Count('device__assigned_to', distinct=True)).order_by('date')
        main_labels = [item['date'].strftime('%d.%m') for item in active_by_date]
        main_values = [item['emp_count'] for item in active_by_date]
        
        # 2. Круговий графік: Розподіл персоналу за поточним статусом безпеки
        status_counts = Employee.objects.values('safety_status').annotate(count=Count('id'))
        status_map = dict(Employee.STATUS_CHOICES)
        color_map = {'OK': '#00c851', 'WARNING': '#ff9800', 'SOS': '#ff4444', 'OFF_SHIFT': '#888888'}
        
        doughnut_labels = [status_map.get(item['safety_status'], item['safety_status']) for item in status_counts]
        doughnut_values = [item['count'] for item in status_counts]
        doughnut_colors = [color_map.get(item['safety_status'], '#4dabf7') for item in status_counts]
        
        emp_qs = Employee.objects.all().order_by('-last_update')
        total_records = emp_qs.count()
        total_pages = (total_records + per_page - 1) // per_page

        # 3. Таблиця: Останні оновлення працівників
        table_rows = []
        for emp in emp_qs[start_idx:end_idx]:
            s_badge = 'bg-success' if emp.safety_status == 'OK' else ('bg-danger' if emp.safety_status == 'SOS' else ('bg-warning text-dark' if emp.safety_status == 'WARNING' else 'bg-secondary'))
            table_rows.append({
                'date': emp.last_update.strftime('%Y-%m-%d %H:%M'), 
                'event_class': 'text-info', 
                'event_text': f'<i class="fas fa-user-clock"></i> Посада: {emp.get_position_display()}', 
                'location': '---', 
                'person': f"{emp.last_name} {emp.first_name[0]}. ({emp.badge_number})", 
                'status_html': f'<span class="badge {s_badge}">{emp.get_safety_status_display()}</span>'
            })
            
        return JsonResponse({
            'chart_main': {'labels': main_labels, 'values': main_values}, 
            'chart_doughnut': {'labels': doughnut_labels, 'values': doughnut_values, 'colors': doughnut_colors}, 
            'table_rows': table_rows,
            'pagination': {'total': total_records, 'pages': total_pages, 'current': page, 'per_page': per_page}
        })

    return JsonResponse({'error': 'Невідомий тип звіту'}, status=400)


@login_required
def equipment_telemetry_api(request):
    """API для отримання поточних показників обладнання (реальна телеметрія)."""
    if request.method == 'GET':
        device_telemetry = {}
        recent_time = timezone.now() - timezone.timedelta(minutes=5)
        
        repeater_clients = {}
        
        latest_log_id = TelemetryLog.objects.filter(
            device=OuterRef('pk')
        ).order_by('-timestamp').values('id')[:1]
        
        devices = MinerDevice.objects.filter(is_active=True).select_related('assigned_to').annotate(latest_log_id=Subquery(latest_log_id))
        log_ids = [d.latest_log_id for d in devices if getattr(d, 'latest_log_id', None)]
        logs_dict = {log.device_id: log for log in TelemetryLog.objects.filter(id__in=log_ids)}

        for device in devices:
            last_log = logs_dict.get(device.id)
            if last_log:
                device_telemetry[device.mac_address] = {
                    'battery': last_log.battery_level,
                    'gas': last_log.gas_level,
                    'temp': last_log.temperature,
                }
                
                # Рахуємо пристрій ТІЛЬКИ на його останньому репітері (якщо дані свіжі)
                if last_log.timestamp >= recent_time and last_log.connected_repeater_id:
                    rep_id = last_log.connected_repeater_id
                    if rep_id not in repeater_clients:
                        repeater_clients[rep_id] = []
                    
                    name = f"{device.assigned_to.last_name} {device.assigned_to.first_name[0]}." if device.assigned_to else device.inventory_number
                    repeater_clients[rep_id].append(name)
        
        repeater_telemetry = {}
        repeaters = InfrastructureDevice.objects.filter(is_active=True)
        for rep in repeaters:
            clients = repeater_clients.get(rep.id, [])
            repeater_telemetry[rep.uid] = {
                'clients': len(clients),
                'clients_list': "\n".join(clients)
            }

        return JsonResponse({'devices': device_telemetry, 'repeaters': repeater_telemetry})
    return JsonResponse({'error': 'GET method required'}, status=405)


@csrf_exempt
@api_key_required
def upload_map_api(request):
    """Приймає JSON з MineCAD та синхронізує репітери."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    try:
        data = json.loads(request.body)
        with transaction.atomic():
            mine_map, _ = MineMap.objects.get_or_create(
                name="Основний горизонт")
            mine_map.map_data = data
            mine_map.save()
            cache.delete('active_mine_map')

            devices = data.get('devices', [])
            if 'tunnels' in data:
                for t in data['tunnels']:
                    devices.extend(t.get('devices', []))

            active_uids = []
            for dev in devices:
                uid = dev.get('id')
                if uid:
                    InfrastructureDevice.objects.update_or_create(
                        uid=uid, defaults={'map_location': mine_map, 'x': dev.get(
                            'x', 0), 'y': dev.get('y', 0), 'is_active': True}
                    )
                    active_uids.append(uid)

            deleted_count, _ = InfrastructureDevice.objects.filter(
                map_location=mine_map).exclude(uid__in=active_uids).delete()
        return JsonResponse({'status': 'success', 'sync': len(active_uids), 'deleted': deleted_count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# --- ПРОФІЛЬ ТА ІНШЕ ---


@login_required
def profile(request):
    UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        u_form, p_form = UserForm(request.POST, instance=request.user), ProfileForm(
            request.POST, request.FILES, instance=request.user.userprofile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, '✅ Профіль оновлено!')
            return redirect('profile')
    else:
        u_form, p_form = UserForm(instance=request.user), ProfileForm(
            instance=request.user.userprofile)
    return render(request, 'diploma/profile.html', {'user_form': u_form, 'profile_form': p_form})


def download_map(request):
    mine_map = get_active_map()
    if not mine_map:
        return HttpResponse("Карта відсутня", status=404)
    response = HttpResponse(json.dumps(
        mine_map.map_data, indent=2), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="mine_map.json"'
    return response

# --- СИМУЛЯТОР ТА API (ДЛЯ ДИПЛОМНОГО ЗАХИСТУ) ---

@login_required
def simulator_view(request):
    """Прихована сторінка пульта керування для генерації даних."""
    employees = Employee.objects.filter(device__isnull=False)
    static_sensors = MinerDevice.objects.filter(is_static=True)
    aps = InfrastructureDevice.objects.filter(is_active=True).order_by('uid')
    return render(request, 'diploma/simulator.html', {'employees': employees, 'static_sensors': static_sensors, 'aps': aps})

@csrf_exempt
@api_key_required
@transaction.atomic
def api_receive_telemetry(request):
    """API для прийому POST-запитів від ESP32 з дедуплікацією тривог."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mac_address = data.get('mac_address')
            ap_uid = data.get('ap_uid', '')
            battery = int(data.get('battery', 100))
            gas_level = float(data.get('gas_level', data.get('gas_co', 0)))
            is_sos = data.get('is_sos', False)
            reason_text = data.get('reason', 'Normal')
            rssi = int(data.get('rssi', 0))  # Зчитуємо RSSI з JSON
            temperature = float(data.get('temperature', 0.0))
            humidity = float(data.get('humidity', 0.0))
            fw_version = data.get('fw_version') # Зчитуємо версію прошивки
            is_moving = data.get('is_moving', True) # Зчитуємо стан руху

            # 1. Знаходимо пристрій по MAC-адресі, а потім працівника
            if not mac_address:
                return JsonResponse({'status': 'error', 'message': 'MAC-адреса пристрою не надана'}, status=400)

            device = MinerDevice.objects.select_related('assigned_to').filter(mac_address__iexact=mac_address).first()

            if not device:
                return JsonResponse({'status': 'error', 'message': f'Пристрій з MAC {mac_address} не зареєстровано'}, status=404)

            # Перевіряємо, чи є команда на перезавантаження
            command = None
            if device.pending_reboot:
                command = "REBOOT"
                device.pending_reboot = False
                device.save()

            # --- ОНОВЛЕННЯ СТАТУСУ АКТИВНОСТІ ПРИСТРОЮ ---
            # Якщо пристрій вийшов на зв'язок і був неактивним, робимо його активним.
            if not device.is_active:
                device.is_active = True
                device.save()

            # --- МИТТЄВА ПЕРЕВІРКА ТА ЛОГУВАННЯ ОНОВЛЕННЯ ПРОШИВКИ ---
            if fw_version and device.firmware_version != fw_version:
                device.firmware_version = fw_version
                device.save()
                OTALog.objects.create(
                    device=device,
                    version=fw_version,
                    status="SUCCESS",
                    message="Оновлення успішно встановлено (підтверджено телеметрією)"
                )

            employee = device.assigned_to
            if not employee:
                # Стаціонарні датчики не мають працівника, але можуть надсилати телеметрію.
                if device.is_static:
                    ap = InfrastructureDevice.objects.filter(Q(wifi_bssid__iexact=ap_uid) | Q(uid__iexact=ap_uid)).first()
                    TelemetryLog.objects.create(
                        device=device,
                        connected_repeater=ap,
                        battery_level=battery,
                        gas_level=gas_level,
                        wifi_signal_strength=rssi,
                        is_sos=is_sos,
                        temperature=temperature,
                        humidity=humidity,
                        is_moving=is_moving
                    )
                    
                    # ТРИВОГА ДЛЯ СТАЦІОНАРНОГО ДАТЧИКА (ГАЗ)
                    if gas_level > 17:
                        alert_reason = f'КРИТИЧНИЙ рівень CH4: {gas_level}% LEL (Евакуація!)' if gas_level >= 50 else f'Перевищення ГДК CH4: {gas_level}% LEL'
                        active_alert = SecurityAlert.objects.filter(device=device, is_resolved=False).first()
                        if not active_alert:
                            SecurityAlert.objects.create(
                                employee=None, device=device, connected_repeater=ap,
                                reason=alert_reason, status='NEW'
                            )
                        else:
                            active_alert.reason = alert_reason
                            active_alert.save()
                            
                    # ТРИВОГА ДЛЯ СТАЦІОНАРНОГО ДАТЧИКА (ЖИВЛЕННЯ 220V)
                    if battery < 99:
                        power_alert_reason = f"Аварія живлення 220V! Датчик працює від АКБ ({battery}%)"
                        recent_bat_time = timezone.now() - timezone.timedelta(hours=8)
                        has_power_alert = SecurityAlert.objects.filter(device=device, reason__icontains="Аварія живлення").filter(
                            Q(is_resolved=False) | Q(created_at__gte=recent_bat_time)
                        ).exists()
                        if not has_power_alert:
                            SecurityAlert.objects.create(
                                employee=None, device=device, connected_repeater=ap,
                                reason=power_alert_reason, status='WARNING'
                            )
                    else:
                        # АВТО-ЗАКРИТТЯ тривоги про "Втрату живлення"
                        power_alerts = SecurityAlert.objects.filter(device=device, is_resolved=False, reason__icontains="Аварія живлення")
                        if power_alerts.exists():
                            power_alerts.update(
                                status='RESOLVED',
                                is_resolved=True,
                                resolved_at=timezone.now(),
                                rescue_notes="Автоматично: Живлення 220V відновлено."
                            )
                            
                    # АВТО-ЗАКРИТТЯ Аварії інфраструктури від стаціонарного датчика
                    if ap:
                        infra_alerts = SecurityAlert.objects.filter(connected_repeater=ap, is_resolved=False, reason__icontains="Аварія інфраструктури")
                        if infra_alerts.exists():
                            infra_alerts.update(
                                status='RESOLVED',
                                is_resolved=True,
                                resolved_at=timezone.now(),
                                rescue_notes="Автоматично: Репітер відновив роботу (отримано телеметрію від датчика)."
                            )
                            
                    return JsonResponse({'status': 'success', 'message': 'Static sensor telemetry logged.', 'command': command})
                return JsonResponse({'status': 'error', 'message': f'Пристрій {device.inventory_number} не прив\'язаний до працівника'}, status=400)

            ap = InfrastructureDevice.objects.filter(Q(wifi_bssid__iexact=ap_uid) | Q(uid__iexact=ap_uid)).first()

            # 2. Завжди створюємо лог (диспетчеру потрібна історія вимірювань)
            TelemetryLog.objects.create(
                device=device,
                connected_repeater=ap,
                battery_level=battery,
                gas_level=gas_level,
                wifi_signal_strength=rssi,
                is_sos=is_sos,
                temperature=temperature,
                humidity=humidity,
                is_moving=is_moving
            )
            
            # --- АВТО-ЗАКРИТТЯ тривоги про "Втрату зв'язку", якщо пристрій знову вийшов на зв'язок ---
            offline_alerts = SecurityAlert.objects.filter(employee=employee, is_resolved=False, reason__icontains="Втрата зв'язку")
            if offline_alerts.exists():
                offline_alerts.update(
                    status='RESOLVED',
                    is_resolved=True,
                    resolved_at=timezone.now(),
                    rescue_notes="Автоматично: Зв'язок відновлено."
                )
                
            # --- АВТО-ЗАКРИТТЯ Аварії інфраструктури, якщо хоча б один пристрій пробився через цей репітер ---
            if ap:
                infra_alerts = SecurityAlert.objects.filter(connected_repeater=ap, is_resolved=False, reason__icontains="Аварія інфраструктури")
                if infra_alerts.exists():
                    infra_alerts.update(
                        status='RESOLVED',
                        is_resolved=True,
                        resolved_at=timezone.now(),
                        rescue_notes="Автоматично: Репітер відновив роботу (отримано телеметрію)."
                    )
            
            # 3. ЛОГІКА ЗАВЕРШЕННЯ ЗМІНИ (Лампова / Док-станція)
            if reason_text == 'END_SHIFT':
                if ap and ap.uid == 'AP-SURFACE':
                    # ПЕРЕВІРКА: Чи є не закриті КРИТИЧНІ тривоги?
                    has_critical = SecurityAlert.objects.filter(employee=employee, is_resolved=False).exclude(status='WARNING').exists()
                    if has_critical:
                        return JsonResponse({'status': 'error', 'message': 'Помилка: Є відкрита КРИТИЧНА тривога! Диспетчер повинен закрити інцидент.'}, status=400)
                    if employee.safety_status != 'OFF_SHIFT':
                        employee.safety_status = 'OFF_SHIFT'
                        employee.save()
                    # Вимикаємо пристрій, оскільки він на зарядці
                    device.is_active = False
                    device.save()
                    return JsonResponse({'status': 'success', 'message': 'Пристрій на зарядці. Зміну завершено.', 'command': command})
                else:
                    return JsonResponse({'status': 'error', 'message': 'Завершення зміни можливе ТІЛЬКИ в Ламповій (AP-SURFACE). Шахтар ще під землею!'}, status=400)

            # 4. ЛОГІКА СКАСУВАННЯ ТРИВОГИ З ПРИСТРОЮ
            if reason_text == 'SOS_CANCELLED':
                active_alert = SecurityAlert.objects.filter(employee=employee, is_resolved=False).first()
                if active_alert:
                    active_alert.status = 'RESOLVED'
                    active_alert.is_resolved = True
                    active_alert.resolved_at = timezone.now()
                    active_alert.rescue_notes = "Автоматично: Тривогу скасовано з пристрою працівником."
                    active_alert.save()
                
                # Перевіряємо чи не лишилося ІНШИХ тривог перед тим як ставити OK
                if not SecurityAlert.objects.filter(employee=employee, is_resolved=False).exists():
                    if employee.safety_status != 'OFF_SHIFT':
                        employee.safety_status = 'OK'
                employee.save()
                
                return JsonResponse({'status': 'success', 'message': 'Alert cancelled by device', 'command': command})

            # 5. ПЕРЕВІРКА КРИТИЧНО НИЗЬКОГО ЗАРЯДУ
            if battery <= 10:
                # Ігноруємо низький заряд, якщо працівник знаходиться в Ламповій (AP-SURFACE)
                if not (ap and ap.uid == 'AP-SURFACE'):
                    # Шукаємо активну тривогу АБО закриту за останні 8 годин (щоб не спамити до кінця зміни)
                    recent_bat_time = timezone.now() - timezone.timedelta(hours=8)
                    has_bat_alert = SecurityAlert.objects.filter(employee=employee, reason__icontains="Низький заряд").filter(
                        Q(is_resolved=False) | Q(created_at__gte=recent_bat_time)
                    ).exists()
                    if not has_bat_alert:
                        SecurityAlert.objects.create(
                            employee=employee, device=device, connected_repeater=ap,
                            reason=f"Низький заряд батареї: {battery}%", status='WARNING'
                        )
                        # Змінюємо статус працівника для жовтого світіння на карті
                        if employee.safety_status == 'OK':
                            employee.safety_status = 'WARNING'

            # 4. ЛОГІКА СТВОРЕННЯ ТРИВОГ (SecurityAlert)
            alert_reason = None
            
            # 1. СПОЧАТКУ перевіряємо об'єктивні сенсори (Газ Метан)
            if gas_level >= 50:
                alert_reason = f'КРИТИЧНИЙ рівень CH4: {gas_level}% LEL (Негайна евакуація!)'
            elif gas_level > 17:
                alert_reason = f'Перевищення ГДК CH4: {gas_level}% LEL'
            # 2. Якщо газ в нормі, але є сигнал is_sos, значить це дійсно ручний виклик
            elif is_sos:
                if 'MANUAL' in reason_text.upper():
                    alert_reason = 'Ручний виклик SOS'
                elif not is_moving or reason_text in ['MAN_DOWN', 'NO_MOVEMENT', 'NO_MOTION', 'Worker immobile', 'FALL']:
                    alert_reason = 'Бездіяльність (Немає руху / Можливе падіння)'
                else:
                    alert_reason = 'Ручний виклик SOS'

            if alert_reason:
                # Шукаємо існуючу НЕВИРІШЕНУ КРИТИЧНУ тривогу (Ігноруємо WARNING-батарею)
                active_alert = SecurityAlert.objects.filter(
                    employee=employee, 
                    is_resolved=False
                ).exclude(status='WARNING').first()

                if not active_alert:
                    # Якщо активної немає — створюємо НОВУ
                    SecurityAlert.objects.create(
                        employee=employee,
                        device=device,
                        connected_repeater=ap,
                        reason=alert_reason,
                        status='NEW'
                    )
                else:
                    # Якщо активна вже є — оновлюємо дані
                    active_alert.connected_repeater = ap
                    
                    # Оновлюємо текст причини, якщо нова причина серйозніша 
                    # (Наприклад, газ виріс з "ГДК" до "КРИТИЧНИЙ", або після кнопки SOS піднявся газ)
                    if "КРИТИЧНИЙ" in alert_reason:
                        active_alert.reason = alert_reason
                    elif "ГДК" in alert_reason and "КРИТИЧНИЙ" not in active_alert.reason:
                        active_alert.reason = alert_reason
                        
                    active_alert.save()
                
                # Ставимо візуальний статус працівнику
                new_status = 'SOS' if (is_sos or gas_level >= 50) else 'WARNING'
                if employee.safety_status != new_status:
                    employee.safety_status = new_status
                    employee.save()
            else:
                # Будь-який нормальний пакет даних від пристрою означає, що працівник на зміні
                # ОНОВЛЕНО: Скидаємо статус на OK ТІЛЬКИ якщо немає не закритих інцидентів
                if not SecurityAlert.objects.filter(employee=employee, is_resolved=False).exists():
                    if employee.safety_status != 'OK':
                        employee.safety_status = 'OK'
                        employee.save()
            return JsonResponse({'status': 'success', 'command': command})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'invalid_method'}, status=405)

def api_active_miners(request):
    """API для віддачі координат активних шахтарів на Карту (mine_map.js)."""
    latest_log_id = TelemetryLog.objects.filter(
        device__assigned_to=OuterRef('pk')
    ).order_by('-timestamp').values('id')[:1]

    miners = Employee.objects.exclude(safety_status='OFF_SHIFT').filter(device__isnull=False).select_related('device').annotate(latest_log_id=Subquery(latest_log_id))
    
    log_ids = [m.latest_log_id for m in miners if getattr(m, 'latest_log_id', None)]
    logs_dict = {log.device_id: log for log in TelemetryLog.objects.filter(id__in=log_ids).select_related('connected_repeater')}

    data = []
    for m in miners:
        last_log = logs_dict.get(m.device.id)
        if last_log and last_log.connected_repeater:
            data.append({
                'id': m.id,
                'name': f"{m.last_name} {m.first_name[0]}.",
                'position': m.get_position_display(),
                'ap_id': last_log.connected_repeater.uid,
                'status': m.safety_status,
                'battery': last_log.battery_level,
                # --- НОВІ ПОЛЯ ---
                'gas': last_log.gas_level,
                'temp': last_log.temperature,
                'hum': last_log.humidity
            })
            
    # Знаходимо штреки, для яких є активні (не закриті) критичні тривоги
    danger_tunnels = set()
    active_danger_alerts = SecurityAlert.objects.filter(
        is_resolved=False,
        connected_repeater__isnull=False
    ).exclude(status='WARNING').select_related('connected_repeater', 'connected_repeater__map_location')
    
    for alert in active_danger_alerts:
        loc = alert.connected_repeater.location_in_mine
        if loc and "Штрек" in loc:
            danger_tunnels.add(loc)
            
    return JsonResponse({'miners': data, 'danger_tunnels': list(danger_tunnels)})

from django.db.models import Q

@csrf_exempt
@api_key_required
def api_get_wifi_networks(request):
    """
    API для отримання списку відомих Wi-Fi мереж.
    Повертає тільки ті пристрої, де SSID не порожній.
    """
    if request.method == 'GET':
        # Фільтруємо: активні ТА (ssid не null ТА ssid не порожній рядок)
        networks = InfrastructureDevice.objects.filter(
            is_active=True, 
            wifi_ssid__isnull=False
        ).exclude(wifi_ssid__exact='')
        
        # Перейменовуємо ключі для ESP32
        network_list = [{'ssid': n.wifi_ssid, 'password': n.wifi_password} for n in networks]
        
        return JsonResponse(network_list, safe=False)
        
    return JsonResponse({'error': 'Only GET method is allowed'}, status=405)

@csrf_exempt
@api_key_required
def api_ota_check(request):
    """API для перевірки наявності OTA-оновлень для ESP32."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Only GET method is allowed'}, status=405)
        
    mac_address = request.GET.get('mac')
    current_version = request.GET.get('version', '1.0.0')
    
    device = None
    if mac_address:
        # Оновлюємо інформацію про поточну версію пристрою в БД
        device = MinerDevice.objects.filter(mac_address__iexact=mac_address).first()
        if device and device.firmware_version != current_version:
            device.firmware_version = current_version
            device.save()
            # Якщо версія відрізняється, значить пристрій успішно прошився та перезавантажився
            OTALog.objects.create(
                device=device,
                version=current_version,
                status="SUCCESS",
                message="Пристрій успішно оновлено та вийшов на зв'язок"
            )
            
    # Шукаємо останню активну прошивку
    latest_firmware = FirmwareUpdate.objects.filter(is_active=True).order_by('-uploaded_at').first()
    
    if latest_firmware and latest_firmware.version != current_version:
        # --- ЛОГІКА ПОСТУПОВОГО РОЗГОРТАННЯ (STAGED ROLLOUT) ---
        if latest_firmware.target_devices.exists():
            # Якщо список не пустий, але пристрій не розпізнано або його немає у списку дозволених -> відмовляємо
            if not device or not latest_firmware.target_devices.filter(id=device.id).exists():
                return JsonResponse({'status': 'up_to_date', 'current_version': current_version, 'message': 'Not in targeted rollout group'})

        # Формуємо абсолютний URL для завантаження (http://91.98.171.31/media/firmwares_esp/...)
        file_url = request.build_absolute_uri(latest_firmware.binary_file.url)
        return JsonResponse({'version': latest_firmware.version, 'url': file_url})
        
    return JsonResponse({'status': 'up_to_date', 'current_version': current_version})

@csrf_exempt
@api_key_required
def api_ota_log(request):
    """API для отримання інформації про помилки OTA з ESP32."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            device = MinerDevice.objects.filter(mac_address__iexact=data.get('mac_address')).first()
            if device:
                OTALog.objects.create(
                    device=device,
                    version=data.get('version', 'unknown'),
                    status=data.get('status', 'FAILED'),
                    message=data.get('message', 'Невідома помилка завантаження')
                )
            return JsonResponse({'status': 'logged'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'POST only'}, status=405)

def personnel_status_api(request):
    """
    API для отримання поточного статусу пристроїв для сторінки персоналу.
    Повертає MAC-адреси пристроїв та їх статус active/inactive.
    """
    if request.method == 'GET':
        statuses = {}
        recent_time = timezone.now() - timezone.timedelta(minutes=5)
        
        latest_log_id = TelemetryLog.objects.filter(
            device=OuterRef('pk')
        ).order_by('-timestamp').values('id')[:1]

        devices = MinerDevice.objects.filter(is_static=False, assigned_to__isnull=False).annotate(latest_log_id=Subquery(latest_log_id))
        log_ids = [d.latest_log_id for d in devices if getattr(d, 'latest_log_id', None)]
        logs_dict = {log.device_id: log for log in TelemetryLog.objects.filter(id__in=log_ids).select_related('connected_repeater')}

        for device in devices:
            location_uid = None
            if device.is_active:
                last_log = logs_dict.get(device.id)
                if last_log and last_log.connected_repeater and last_log.timestamp >= recent_time:
                    location_uid = last_log.connected_repeater.uid
                    
            statuses[device.mac_address] = {
                'is_active': device.is_active,
                'inventory_number': device.inventory_number,
                'location': location_uid
            }
            
        return JsonResponse({'device_statuses': statuses})
    return JsonResponse({'error': 'GET method required'}, status=405)