from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
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
    
    # Показники для віджетів
    latest_telemetry = TelemetryLog.objects.order_by('-timestamp').first()
    mine_map = get_active_map()

    context = {
        'online_count': online_staff.count(),
        'warning_count': Employee.objects.filter(safety_status__in=['WARNING', 'SOS']).count(),
        'recent_staff': online_staff.order_by('-last_update')[:4],
        'active_alerts': SecurityAlert.objects.filter(is_resolved=False).order_by('-created_at')[:5],
        'critical_alerts_count': SecurityAlert.objects.filter(is_resolved=False).count(),
        'avg_temp': latest_telemetry.temperature if latest_telemetry else 0.0,
        'avg_hum': latest_telemetry.humidity if latest_telemetry else 0.0,
        'gas_level': latest_telemetry.gas_level if latest_telemetry else 0,
        'map_data': json.dumps(mine_map.map_data) if mine_map else "{}",
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
    lamps = MinerDevice.objects.filter(is_static=False).select_related('assigned_to')
    sensors = MinerDevice.objects.filter(is_static=True)
    repeaters = InfrastructureDevice.objects.select_related('map_location')
    
    return render(request, 'diploma/equipment.html', {
        'lamps': lamps, 'sensors': sensors, 'repeaters': repeaters,
        'total_devices': lamps.count() + sensors.count() + repeaters.count()
    })

@login_required
def mine_map(request):
    """Повноекранна інтерактивна карта."""
    mine_map = get_active_map()
    return render(request, 'diploma/mine_map.html', {
        'map_data': json.dumps(mine_map.map_data if mine_map else {}),
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
        messages.success(request, f"Статус оновлено: {alert.get_status_display()}")
        return redirect('alert_detail', alert_id=alert.id)
        
    latest_telemetry = TelemetryLog.objects.filter(device=alert.device).order_by('-timestamp').first()
    return render(request, 'diploma/alert_detail.html', {'alert': alert, 'telemetry': latest_telemetry})

# --- API ЕНДПОІНТИ (ДЛЯ JS ТА ЗОВНІШНІХ ПРОГРАМ) ---

def active_alerts_api(request):
    try:
        # 1. Отримуємо тривоги
        alerts = SecurityAlert.objects.filter(is_resolved=False).order_by('-created_at')
        alerts_list = []
        for a in alerts:
            alerts_list.append({
                'id': a.id,
                'reason': a.get_reason_display() if hasattr(a, 'get_reason_display') else str(a.reason),
                'employee': a.employee.last_name if a.employee else "---",
                'location': a.location_label or "Шахта",
                'time': a.created_at.strftime('%H:%M'),
                'is_critical': True
            })

        # 2. Отримуємо персонал (свіжі статуси)
        staff = Employee.objects.exclude(safety_status='OFF_SHIFT').order_by('-last_update')[:4]
        staff_list = []
        for s in staff:
            staff_list.append({
                'full_name': f"{s.first_name} {s.last_name}",
                'position': s.get_position_display(),
                'status': s.safety_status, # 'OK', 'WARNING', 'SOS'
                'photo_url': s.photo.url if s.photo else None
            })
            
        return JsonResponse({
            'count': alerts.count(),
            'alerts': alerts_list,
            'staff': staff_list
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def alert_telemetry_api(request, alert_id):
    """Повертає свіжу телеметрію для конкретної тривоги."""
    alert = get_object_or_404(SecurityAlert, id=alert_id)
    latest = TelemetryLog.objects.filter(device=alert.device).order_by('-timestamp').first()
    if not latest: return JsonResponse({'status': 'no_data'})
    return JsonResponse({
        'status': 'ok', 'gas': latest.gas_level, 'temp': latest.temperature,
        'moving': latest.is_moving, 'rssi': latest.wifi_signal_strength,
        'timestamp': latest.timestamp.strftime('%H:%M:%S'),
        'repeater': latest.connected_repeater.uid if latest.connected_repeater else "Втрачено"
    })

@csrf_exempt
def upload_map_api(request):
    """Приймає JSON з MineCAD та синхронізує репітери."""
    if request.method != 'POST': return JsonResponse({'error': 'POST only'}, status=405)
    try:
        data = json.loads(request.body)
        with transaction.atomic():
            mine_map, _ = MineMap.objects.get_or_create(name="Основний горизонт")
            mine_map.map_data = data
            mine_map.save()
            
            devices = data.get('devices', [])
            if 'tunnels' in data:
                for t in data['tunnels']: devices.extend(t.get('devices', []))

            active_uids = []
            for dev in devices:
                uid = dev.get('id')
                if uid:
                    InfrastructureDevice.objects.update_or_create(
                        uid=uid, defaults={'map_location': mine_map, 'x': dev.get('x', 0), 'y': dev.get('y', 0), 'is_active': True}
                    )
                    active_uids.append(uid)
            
            deleted_count, _ = InfrastructureDevice.objects.filter(map_location=mine_map).exclude(uid__in=active_uids).delete()
        return JsonResponse({'status': 'success', 'sync': len(active_uids), 'deleted': deleted_count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# --- ПРОФІЛЬ ТА ІНШЕ ---

@login_required
def profile(request):
    UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        u_form, p_form = UserForm(request.POST, instance=request.user), ProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save(); p_form.save()
            messages.success(request, '✅ Профіль оновлено!')
            return redirect('profile')
    else:
        u_form, p_form = UserForm(instance=request.user), ProfileForm(instance=request.user.userprofile)
    return render(request, 'diploma/profile.html', {'user_form': u_form, 'profile_form': p_form})

def download_map(request):
    mine_map = get_active_map()
    if not mine_map: return HttpResponse("Карта відсутня", status=404)
    response = HttpResponse(json.dumps(mine_map.map_data, indent=2), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="mine_map.json"'
    return response