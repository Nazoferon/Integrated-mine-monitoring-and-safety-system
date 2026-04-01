from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg, Max, Count, Q
from django.db.models.functions import TruncDate
from django.utils.dateparse import parse_date
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
import json

from .forms import UserForm, ProfileForm
from .models import MineMap, UserProfile, InfrastructureDevice, Employee, MinerDevice, SecurityAlert, TelemetryLog

# --- ДОПОМІЖНА ФУНКЦІЯ ---


def get_active_map():
    """Повертає актуальну карту шахти."""
    return MineMap.objects.filter(name="Основний горизонт").first() or \
        MineMap.objects.order_by('-updated_at').first()

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

    context = {
        'online_count': online_staff.count(),
        'warning_count': alerts_count,
        'recent_staff': online_staff.order_by('-last_update')[:4],
        'active_alerts': active_alerts_query.order_by('-created_at')[:5],
        'critical_alerts_count': alerts_count,
        'avg_temp': stats['avg_temp'] if stats['avg_temp'] is not None else 0.0,
        'avg_hum': stats['avg_hum'] if stats['avg_hum'] is not None else 0.0,
        'gas_level': stats['max_gas'] if stats['max_gas'] is not None else 0,
        'map_data': mine_map.map_data if mine_map else {},
    }
    return render(request, 'diploma/diploma_home.html', context)


@login_required
def personnel_list(request):
    """Список персоналу."""
    employees = Employee.objects.all().select_related('device')
    return render(request, 'diploma/personnel.html', {
        'employees': employees,
        'total_employees': employees.count()
    })


@login_required
def equipment_list(request):
    """Парк обладнання (коногонки, датчики, репітери)."""
    lamps = MinerDevice.objects.filter(
        is_static=False).select_related('assigned_to')
    sensors = MinerDevice.objects.filter(is_static=True)
    repeaters = InfrastructureDevice.objects.select_related('map_location')

    return render(request, 'diploma/equipment.html', {
        'lamps': lamps, 'sensors': sensors, 'repeaters': repeaters,
        'total_devices': lamps.count() + sensors.count() + repeaters.count()
    })


@login_required
def reports_view(request):
    # Поки що просто рендеримо шаблон. 
    # Пізніше сюди можна додати реальну вибірку з бази даних.
    return render(request, 'diploma/reports.html')

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
                emp.safety_status = 'OK'
                emp.save()
            elif new_status == 'IN_PROGRESS':
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
    active_alerts = SecurityAlert.objects.filter(is_resolved=False).order_by('-created_at')[:5]
    alerts_html = render_to_string('diploma/_alert_list.html', {
        'active_alerts': active_alerts,
        'request': request  # Передаємо request для роботи `url` тега
    })

    return JsonResponse({
        'avg_temp': stats['avg_temp'] if stats['avg_temp'] is not None else 0.0,
        'avg_hum': stats['avg_hum'] if stats['avg_hum'] is not None else 0.0,
        'gas_level': stats['max_gas'] if stats['max_gas'] is not None else 0,
        'online_count': online_count,
        'warning_count': warning_count,
        'new_alerts_count': new_alerts_count,
        'alerts_html': alerts_html, # Додаємо HTML до відповіді
    })

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
        gas_count = alerts.filter(reason__icontains='CO').count()
        other_count = alerts.exclude(reason__icontains='SOS').exclude(reason__icontains='CO').count()
        
        doughnut_labels = ['Кнопка SOS', 'Газ (CO)', 'Інше']
        doughnut_values = [sos_count, gas_count, other_count]
        doughnut_colors = ['#ff4444', '#ff9800', '#ffd700']
        
        # 3. Рядки для таблиці
        table_rows = []
        for alert in alerts.order_by('-created_at')[:100]:
            status_classes = {'RESOLVED': ('bg-success', 'Вирішено', 'text-muted'), 'IN_PROGRESS': ('bg-warning text-dark', 'В роботі', 'text-warning')}
            s_badge, s_text, e_class = status_classes.get(alert.status, ('bg-danger', 'Нова', 'text-danger'))
                
            table_rows.append({
                'date': alert.created_at.strftime('%Y-%m-%d %H:%M'),
                'event_class': e_class,
                'event_text': f'<i class="fas fa-exclamation-triangle"></i> {alert.reason}',
                'location': alert.location_label or 'Невідомо',
                'person': f"{alert.employee.last_name} {alert.employee.first_name[0]}. ({alert.device.inventory_number})" if alert.employee and alert.device else '---',
                'status_html': f'<span class="badge {s_badge}">{s_text}</span>'
            })
            
        return JsonResponse({
            'chart_main': {'labels': main_labels, 'values': main_values},
            'chart_doughnut': {'labels': doughnut_labels, 'values': doughnut_values, 'colors': doughnut_colors},
            'table_rows': table_rows
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
        
        doughnut_labels = ['Норма (<10 ppm)', 'Увага (10-50 ppm)', 'Небезпека (>50 ppm)']
        doughnut_values = [safe_count, warning_count, danger_count]
        doughnut_colors = ['#00c851', '#ff9800', '#ff4444']
        
        # 3. Рядки для таблиці (Топ-100 записів з найвищим показником газу)
        table_rows = []
        for log in logs.order_by('-gas_level', '-timestamp')[:100]:
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
                'event_text': f'<i class="fas fa-wind"></i> Газ: {log.gas_level} ppm | Темп: {log.temperature}°C',
                'location': location,
                'person': person_info,
                'status_html': f'<span class="badge {s_badge}">{s_text}</span>'
            })
            
        return JsonResponse({
            'chart_main': {'labels': main_labels, 'values': main_values},
            'chart_doughnut': {'labels': doughnut_labels, 'values': doughnut_values, 'colors': doughnut_colors},
            'table_rows': table_rows
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
        
        # 3. Таблиця: Топ-100 записів із найнижчим зарядом або поганим сигналом
        table_rows = []
        for log in logs.order_by('battery_level', '-timestamp')[:100]:
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
            
        return JsonResponse({'chart_main': {'labels': main_labels, 'values': main_values}, 'chart_doughnut': {'labels': doughnut_labels, 'values': doughnut_values, 'colors': doughnut_colors}, 'table_rows': table_rows})

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
        
        # 3. Таблиця: Останні оновлення працівників
        table_rows = []
        for emp in Employee.objects.all().order_by('-last_update')[:100]:
            s_badge = 'bg-success' if emp.safety_status == 'OK' else ('bg-danger' if emp.safety_status == 'SOS' else ('bg-warning text-dark' if emp.safety_status == 'WARNING' else 'bg-secondary'))
            table_rows.append({
                'date': emp.last_update.strftime('%Y-%m-%d %H:%M'), 
                'event_class': 'text-info', 
                'event_text': f'<i class="fas fa-user-clock"></i> Посада: {emp.get_position_display()}', 
                'location': '---', 
                'person': f"{emp.last_name} {emp.first_name[0]}. ({emp.badge_number})", 
                'status_html': f'<span class="badge {s_badge}">{emp.get_safety_status_display()}</span>'
            })
            
        return JsonResponse({'chart_main': {'labels': main_labels, 'values': main_values}, 'chart_doughnut': {'labels': doughnut_labels, 'values': doughnut_values, 'colors': doughnut_colors}, 'table_rows': table_rows})

    return JsonResponse({'error': 'Невідомий тип звіту'}, status=400)


@csrf_exempt
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
    aps = InfrastructureDevice.objects.filter(is_active=True).order_by('uid')
    return render(request, 'diploma/simulator.html', {'employees': employees, 'aps': aps})

@csrf_exempt
def api_receive_telemetry(request):
    """API для прийому POST-запитів від ESP32 з дедуплікацією тривог."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mac_address = data.get('mac_address')
            ap_uid = data.get('ap_uid', '')
            battery = int(data.get('battery', 100))
            gas_co = float(data.get('gas_co', 0))
            is_sos = data.get('is_sos', False)

            # 1. Знаходимо пристрій по MAC-адресі, а потім працівника
            if not mac_address:
                return JsonResponse({'status': 'error', 'message': 'MAC-адреса пристрою не надана'}, status=400)

            device = MinerDevice.objects.select_related('assigned_to').filter(mac_address__iexact=mac_address).first()

            if not device:
                return JsonResponse({'status': 'error', 'message': f'Пристрій з MAC {mac_address} не зареєстровано'}, status=404)

            employee = device.assigned_to
            if not employee:
                # Стаціонарні датчики не мають працівника, але можуть надсилати телеметрію.
                if device.is_static:
                    ap = InfrastructureDevice.objects.filter(wifi_bssid__iexact=ap_uid).first()
                    TelemetryLog.objects.create(
                        device=device,
                        connected_repeater=ap,
                        battery_level=battery,
                        gas_level=gas_co,
                        is_sos=is_sos,
                        temperature=24.5,
                        humidity=65.0
                    )
                    return JsonResponse({'status': 'success', 'message': 'Static sensor telemetry logged.'})
                return JsonResponse({'status': 'error', 'message': f'Пристрій {device.inventory_number} не прив\'язаний до працівника'}, status=400)

            ap = InfrastructureDevice.objects.filter(wifi_bssid__iexact=ap_uid).first()

            # 2. Завжди створюємо лог (диспетчеру потрібна історія вимірювань)
            TelemetryLog.objects.create(
                device=device,
                connected_repeater=ap,
                battery_level=battery,
                gas_level=gas_co,
                is_sos=is_sos,
                temperature=24.5, 
                humidity=65.0
            )

            # 3. ЛОГІКА ТРИВОГ (SecurityAlert)
            alert_reason = None
            if is_sos:
                alert_reason = 'Ручний виклик SOS'
            elif gas_co >= 50:
                alert_reason = f'КРИТИЧНИЙ рівень CO: {gas_co} ppm (Негайна евакуація!)'
            elif gas_co > 17:
                alert_reason = f'Перевищення ГДК CO: {gas_co} ppm'

            if alert_reason:
                # Перевіряємо, чи вже є ВІДКРИТА тривога для цього працівника
                # Відкритою вважається та, де is_resolved=False
                active_alert = SecurityAlert.objects.filter(
                    employee=employee, 
                    is_resolved=False
                ).first()

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
                    # Якщо активна вже є — просто оновлюємо дані в ній (щоб диспетчер бачив актуальне місце)
                    active_alert.connected_repeater = ap
                    # Якщо нова причина серйозніша за попередню, можемо оновити текст
                    if "КРИТИЧНИЙ" in alert_reason and "ГДК" in active_alert.reason:
                        active_alert.reason = alert_reason
                    active_alert.save()
                
                # Ставимо візуальний статус працівнику
                employee.safety_status = 'SOS' if (is_sos or gas_co >= 50) else 'WARNING'
            else:
                # Якщо все в нормі — ставимо статус OK (але не закриваємо тривоги автоматично!)
                # Тривогу має закрити ЛЮДИНА (диспетчер), щоб переконатися, що все добре.
                if employee.safety_status != 'OFF_SHIFT':
                    employee.safety_status = 'OK'

            employee.save()
            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'invalid_method'}, status=405)

def api_active_miners(request):
    """API для віддачі координат активних шахтарів на Карту (mine_map.js)."""
    miners = Employee.objects.exclude(safety_status='OFF_SHIFT').filter(device__isnull=False)
    data = []
    for m in miners:
        last_log = TelemetryLog.objects.filter(device=m.device).order_by('-timestamp').first()
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
    return JsonResponse({'miners': data})

from django.db.models import Q

@csrf_exempt
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