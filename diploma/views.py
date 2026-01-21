from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib.auth.views import PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
import json

# Імпорт ваших моделей (переконайтесь, що вони є в models.py)
from .forms import UserForm, ProfileForm
from .models import MineMap, UserProfile, InfrastructureDevice

@login_required
def diploma_home(request):
    return render(request, 'diploma/diploma_home.html')

@login_required
def profile(request):
    # Автоматично створюємо профіль, якщо його немає
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

# --- API ДЛЯ MINECAD (Завантаження карти з програми) ---
@csrf_exempt
def upload_map_api(request):
    """
    Приймає JSON з настільної програми MineCAD.
    Зберігає карту та оновлює список пристроїв.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            with transaction.atomic():
                # 1. Створюємо або оновлюємо карту
                # Можна створювати нову щоразу для історії, або оновлювати одну
                new_map = MineMap.objects.create(
                    name=f"Mine Map (Upload {data.get('timestamp', '')})",
                    map_data=data,
                    last_edited_by=request.user if request.user.is_authenticated else None
                )
                
                # 2. Оновлюємо таблицю фізичних пристроїв
                created_count = 0
                
                # Якщо пристрої вкладені в тунелі (структура MineCAD v29)
                if 'tunnels' in data:
                    for tunnel in data['tunnels']:
                        if 'devices' in tunnel:
                            for dev in tunnel['devices']:
                                InfrastructureDevice.objects.update_or_create(
                                    uid=dev['id'],
                                    defaults={
                                        'device_type': 'WIFI_REP',
                                        'map_location': new_map,
                                        'x': dev['x'],
                                        'y': dev['y'],
                                        'status': 'ONLINE'
                                    }
                                )
                                created_count += 1
                                
                # Якщо є окремий список 'yards' або інші, їх теж можна обробити тут

            return JsonResponse({
                'status': 'success', 
                'message': f'Карту збережено! Оновлено пристроїв: {created_count}',
                'map_id': new_map.id
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

# --- ПЕРЕГЛЯД КАРТИ НА САЙТІ ---
@login_required
def mine_map(request):
    """
    Відображення останньої актуальної карти на веб-сторінці.
    """
    # Беремо останню завантажену карту
    mine_map = MineMap.objects.order_by('-created_at').first()
    
    map_data = mine_map.map_data if mine_map else {}
    last_edited = mine_map.last_edited_by.username if mine_map and mine_map.last_edited_by else 'Система'
    
    return render(request, 'diploma/mine_map.html', {
        'map_data': json.dumps(map_data),
        'last_edited_by': last_edited,
        'map_name': mine_map.name if mine_map else "Немає даних"
    })

@login_required
def download_map(request):
    """Завантаження JSON файлу карти"""
    mine_map = MineMap.objects.order_by('-created_at').first()
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