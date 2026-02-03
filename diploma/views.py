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
from .models import MineMap, UserProfile, InfrastructureDevice

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

# --- API: ЗАВАНТАЖЕННЯ КАРТИ ТА СИНХРОНІЗАЦІЯ РЕПІТЕРІВ ---
@csrf_exempt
def upload_map_api(request):
    """
    Приймає JSON з MineCAD.
    1. Оновлює карту "Основний горизонт".
    2. Автоматично створює або оновлює координати репітерів.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            with transaction.atomic():
                # 1. Працюємо з однією картою (оновлюємо її, а не створюємо нову)
                mine_map, created = MineMap.objects.get_or_create(
                    name="Основний горизонт"
                )
                # Оновлюємо JSON дані карти
                mine_map.map_data = data
                mine_map.save()
                
                # 2. Витягуємо список пристроїв для синхронізації
                devices_list = []
                
                # Підтримка нової структури (плоский список devices)
                if 'devices' in data:
                    devices_list.extend(data['devices'])
                
                # Підтримка вкладеної структури (tunnels -> devices)
                if 'tunnels' in data:
                    for tunnel in data['tunnels']:
                        if 'devices' in tunnel:
                            devices_list.extend(tunnel['devices'])

                # 3. Синхронізація таблиці InfrastructureDevice
                updated_count = 0
                active_uids = [] # Збережемо ID, які прийшли в цьому запиті

                for dev in devices_list:
                    uid = dev.get('id')
                    if uid:
                        # update_or_create: якщо репітер вже є - оновить координати, якщо ні - створить
                        # Поле wifi_bssid не чіпаємо (воно заповнюється вручну в адмінці)
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
                        updated_count += 1
                
                # (Опціонально) Можна деактивувати репітери, яких більше немає на карті
                # InfrastructureDevice.objects.filter(map_location=mine_map).exclude(uid__in=active_uids).update(is_active=False)

            return JsonResponse({
                'status': 'success', 
                'message': f'Карту оновлено! Синхронізовано репітерів: {updated_count}',
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