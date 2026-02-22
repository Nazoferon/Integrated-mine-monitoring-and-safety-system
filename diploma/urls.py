from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.diploma_home, name='diploma_home'),  # Головна сторінка
    path('profile/', views.profile, name='profile'),  # Профіль
    path('mine_map/', views.mine_map, name='mine_map'),  # Перегляд карти
    path('download_map/', views.download_map, name='download_map'), # Завантаження карти
    path('personnel/', views.personnel_list, name='personnel'),  # Персонал
    path('equipment/', views.equipment_list, name='equipment'),  # Обладнання
    
    
    path('api/upload-map/', views.upload_map_api, name='upload_map_api'), # --- НОВЕ API ДЛЯ ЗАВАНТАЖЕННЯ КАРТИ З ПРОГРАМИ ---
    path('alert/<int:alert_id>/', views.alert_detail, name='alert_detail'),  # --- API для оновлення даних з програми ---
    path('alert/<int:alert_id>/api/', views.alert_telemetry_api, name='alert_telemetry_api'), # --- API для оновлення даних з програми ---

    # URL для скидання пароля
    path('password-reset/', 
      auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt'
      ), 
      name='password_reset'),
    
    path('password-reset/done/', 
      auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
      ), 
      name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
      auth_views.PasswordResetConfirmView.as_view(
          template_name='registration/password_reset_confirm.html'
      ), 
      name='password_reset_confirm'),
    
    path('password-reset-complete/', 
      auth_views.PasswordResetCompleteView.as_view(
          template_name='registration/password_reset_complete.html'
      ), 
      name='password_reset_complete'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)