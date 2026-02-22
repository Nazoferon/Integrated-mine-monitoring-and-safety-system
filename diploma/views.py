from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib.auth.views import PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
import json

from .forms import UserForm, ProfileForm
# Імпортуємо нові моделі
from .models import MineMap, UserProfile, InfrastructureDevice, Employee, MinerDevice

@login_required
def diploma_home(request):
    return render(request, 'diploma/diploma_home.html')

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