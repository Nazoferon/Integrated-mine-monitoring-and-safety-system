from django.shortcuts import render, redirect # Імпортуємо redirect для перенаправлення
from django.contrib.auth.decorators import login_required
from .forms import UserForm, ProfileForm
from django.contrib import messages
from .models import MineMap
import json

from django.contrib.auth.views import PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin

@login_required
def diploma_home(request):
    return render(request, 'diploma/diploma_home.html')


@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)  # ЗМІНИТЬ ЦЕ
        profile_form = ProfileForm(request.POST, request.FILES, instance=request.user.userprofile)  # ЗМІНИТЬ ЦЕ
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, '✅ Профіль успішно оновлено!')
            return redirect('profile')
    else:
        user_form = UserForm(instance=request.user)  # ЗМІНИТЬ ЦЕ
        profile_form = ProfileForm(instance=request.user.userprofile)  # ЗМІНИТЬ ЦЕ
    
    return render(request, 'diploma/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


@login_required
def mine_map(request):
    if request.method == 'POST':
        map_data = json.loads(request.POST.get('map_data', '{}'))
        mine_map, created = MineMap.objects.get_or_create(
            name="Mine Map",
            defaults={'map_data': map_data, 'last_edited_by': request.user}
        )
        if not created:
            mine_map.map_data = map_data
            mine_map.last_edited_by = request.user
            mine_map.save()
        return JsonResponse({
            'status': 'success',
            'map_data': mine_map.map_data,
            'last_edited_by': mine_map.last_edited_by.username if mine_map.last_edited_by else 'Невідомо'
        })
    else:
        mine_map = MineMap.objects.filter(name="Mine Map").first()
        map_data = mine_map.map_data if mine_map else {}
        last_edited_by = mine_map.last_edited_by.username if mine_map and mine_map.last_edited_by else 'Невідомо'
        return render(request, 'diploma/mine_map.html', {
            'map_data': json.dumps(map_data),
            'last_edited_by': last_edited_by
        })

@login_required
def download_map(request):
    mine_map = MineMap.objects.filter(name="Mine Map").first()
    if not mine_map:
        return HttpResponse(status=404)
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