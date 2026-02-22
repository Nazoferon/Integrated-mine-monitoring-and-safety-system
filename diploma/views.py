from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib.auth.views import PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404
from django.utils import timezone
import json

from .forms import UserForm, ProfileForm
# Імпортуємо нові моделі
from .models import MineMap, UserProfile, InfrastructureDevice, Employee, MinerDevice, SecurityAlert, TelemetryLog

@login_required
def diploma_home(request):
    # 1. Статистика по персоналу
    # Вважаємо, що працівник "в шахті", якщо його статус НЕ 'OFF_SHIFT'
    online_staff = Employee.objects.exclude(safety_status='OFF_SHIFT')
    online_count = online_staff.count()
    
    # Кількість попереджень і тривог
    warning_count = Employee.objects.filter(safety_status__in=['WARNING', 'SOS']).count()
    
    # Беремо 4 останніх оновлених працівників для бічної панелі
    recent_staff = online_staff.order_by('-last_update')[:4]

    # 2. Тривоги та Сповіщення
    # Беремо всі невирішені тривоги
    active_alerts = SecurityAlert.objects.filter(is_resolved=False).order_by('-created_at')[:5]
    critical_alerts_count = active_alerts.count()

    # 3. Телеметрія (Показники середовища)
    # Беремо останній запис телеметрії для виведення середніх/останніх показників
    latest_telemetry = TelemetryLog.objects.order_by('-timestamp').first()
    
    avg_temp = latest_telemetry.temperature if latest_telemetry and latest_telemetry.temperature else 0.0
    avg_hum = latest_telemetry.humidity if latest_telemetry and latest_telemetry.humidity else 0.0
    gas_level = latest_telemetry.gas_level if latest_telemetry and latest_telemetry.gas_level else 0

    context = {
        'online_count': online_count,
        'warning_count': warning_count,
        'recent_staff': recent_staff,
        'active_alerts': active_alerts,
        'critical_alerts_count': critical_alerts_count,
        'avg_temp': avg_temp,
        'avg_hum': avg_hum,
        'gas_level': gas_level,
    }
    
    return render(request, 'diploma/diploma_home.html', context)

def alert_telemetry_api(request, alert_id):
    alert = get_object_or_404(SecurityAlert, id=alert_id)
    latest = TelemetryLog.objects.filter(device=alert.device).order_by('-timestamp').first()
    
    if not latest:
        return JsonResponse({'status': 'no_data'})
        
    return JsonResponse({
        'status': 'ok',
        'timestamp': latest.timestamp.strftime('%H:%M:%S'),
        'gas': latest.gas_level,
        'temp': latest.temperature,
        'moving': latest.is_moving,
        'rssi': latest.wifi_signal_strength,
        'repeater': latest.connected_repeater.uid if latest.connected_repeater else "Втрачено"
    })

def alert_detail(request, alert_id):
    alert = get_object_or_404(SecurityAlert, id=alert_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('rescue_notes')
        
        # Оновлюємо статус
        if new_status:
            alert.status = new_status
            
            # Якщо диспетчер закриває тривогу
            if new_status == 'RESOLVED':
                alert.is_resolved = True
                alert.resolved_at = timezone.now()
                alert.resolved_by = request.user
                
                # АВТОМАТИКА: Повертаємо працівнику нормальний статус
                emp = alert.employee
                emp.safety_status = 'OK'
                emp.save()
                
            # Якщо диспетчер щойно взяв у роботу (відправив рятувальників)
            elif new_status == 'IN_PROGRESS':
                alert.is_resolved = False
                alert.resolved_at = None
        
        # Оновлюємо нотатки
        if notes is not None:
            alert.rescue_notes = notes
            
        alert.save()
        messages.success(request, f"Статус тривоги оновлено на: {alert.get_status_display()}")
        return redirect('alert_detail', alert_id=alert.id)
        
    # Отримуємо останні показники телеметрії з коногонки, яка дала збій
    latest_telemetry = TelemetryLog.objects.filter(device=alert.device).order_by('-timestamp').first()
    
    return render(request, 'diploma/alert_detail.html', {
      'alert': alert,
      'telemetry': latest_telemetry
    })

@login_required
def profile(request):
    if not hasattr(request.user, 'userprofile'):
        UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, '✅ Профіль успішно оновлено!')
            return redirect('profile')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = ProfileForm(instance=request.user.userprofile)
    
    return render(request, 'diploma/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

def personnel_list(request):
    # Отримуємо всіх працівників. 
    # Якщо пристрій прив'язаний через OneToOneField (related_name='device'),
    # використовуємо select_related для оптимізації БД.
    employees = Employee.objects.all().select_related('device')
    
    context = {
        'employees': employees,
        'total_employees': employees.count(),
    }
    return render(request, 'diploma/personnel.html', context)

def equipment_list(request):
    # Мобільні пристрої (Коногонки)
    lamps = MinerDevice.objects.filter(is_static=False).select_related('assigned_to')
    
    # Стаціонарні датчики
    sensors = MinerDevice.objects.filter(is_static=True)
    
    # Wi-Fi інфраструктура (Репітери)
    repeaters = InfrastructureDevice.objects.select_related('map_location')
    
    context = {
        'lamps': lamps,
        'sensors': sensors,
        'repeaters': repeaters,
        'total_lamps': lamps.count(),
        'total_sensors': sensors.count(),
        'total_repeaters': repeaters.count(),
        'total_devices': lamps.count() + sensors.count() + repeaters.count(),
    }
    return render(request, 'diploma/equipment.html', context)

# --- API: ЗАВАНТАЖЕННЯ КАРТИ ТА СИНХРОНІЗАЦІЯ РЕПІТЕРІВ ---
@csrf_exempt
def upload_map_api(request):
    """
    Приймає JSON з MineCAD.
    Повна синхронізація: Створення нових + Оновлення існуючих + ВИДАЛЕННЯ зниклих.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            with transaction.atomic():
                # 1. Отримуємо або створюємо карту
                mine_map, created = MineMap.objects.get_or_create(
                    name="Основний горизонт"
                )
                mine_map.map_data = data
                mine_map.save()
                
                # 2. Формуємо єдиний список пристроїв з JSON
                devices_list = []
                
                # Підтримка нової структури MineCAD
                if 'devices' in data:
                    devices_list.extend(data['devices'])
                
                # Підтримка старої структури (вкладені в тунелі)
                if 'tunnels' in data:
                    for tunnel in data['tunnels']:
                        if 'devices' in tunnel:
                            devices_list.extend(tunnel['devices'])

                # 3. Синхронізація (Upsert)
                # Збираємо список UID, які ДІЙСНО є на новій карті
                active_uids = [] 

                for dev in devices_list:
                    uid = dev.get('id')
                    if uid:
                        # Створюємо або оновлюємо
                        InfrastructureDevice.objects.update_or_create(
                            uid=uid,
                            defaults={
                                'map_location': mine_map,
                                'x': dev.get('x', 0),
                                'y': dev.get('y', 0),
                                'is_active': True
                            }
                        )
                        active_uids.append(uid)
                
                # 4. ОЧИЩЕННЯ (Garbage Collection)
                # Видаляємо всі репітери цієї карти, чиїх UID немає в списку active_uids
                deleted_count, _ = InfrastructureDevice.objects.filter(map_location=mine_map).exclude(uid__in=active_uids).delete()

            return JsonResponse({
                'status': 'success', 
                'message': f'Карту оновлено! Синхронізовано: {len(active_uids)}. Видалено старих: {deleted_count}.',
                'map_id': mine_map.id
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

# --- ПЕРЕГЛЯД КАРТИ ---
@login_required
def mine_map(request):
    """
    Відображення карти. Беремо "Основний горизонт" або останню оновленую.
    """
    # Спробуємо знайти карту за назвою, або візьмемо першу ліпшу
    mine_map = MineMap.objects.filter(name="Основний горизонт").first()
    if not mine_map:
        mine_map = MineMap.objects.order_by('-updated_at').first()
    
    map_data = mine_map.map_data if mine_map else {}
    
    return render(request, 'diploma/mine_map.html', {
        'map_data': json.dumps(map_data),
        'map_name': mine_map.name if mine_map else "Немає даних"
    })

@login_required
def download_map(request):
    """Завантаження JSON файлу карти"""
    mine_map = MineMap.objects.filter(name="Основний горизонт").first()
    if not mine_map:
        mine_map = MineMap.objects.order_by('-updated_at').first()

    if not mine_map:
        return HttpResponse("Карта ще не створена", status=404)
        
    response = HttpResponse(
        content=json.dumps(mine_map.map_data, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = 'attachment; filename="mine_map.json"'
    return response

class CustomPasswordResetView(SuccessMessageMixin, PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_message = "Ми надіслали вам інструкції для скидання пароля на вказану електронну адресу."