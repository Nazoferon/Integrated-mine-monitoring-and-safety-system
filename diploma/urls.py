from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Головні сторінки
    path('', views.diploma_home, name='diploma_home'),
    path('profile/', views.profile, name='profile'),
    path('personnel/', views.personnel_list, name='personnel'),
    path('equipment/', views.equipment_list, name='equipment'),
    
    # Карта та інструменти
    path('mine_map/', views.mine_map, name='mine_map'),
    path('download_map/', views.download_map, name='download_map'),
    
    # Інциденти та Телеметрія
    path('alert/<int:alert_id>/', views.alert_detail, name='alert_detail'),
    
    # API ендпоінти
    path('api/active-alerts/', views.active_alerts_api, name='active_alerts_api'),
    path('api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('api/upload-map/', views.upload_map_api, name='upload_map_api'),
    path('alert/<int:alert_id>/api/', views.alert_telemetry_api, name='alert_telemetry_api'),

    # Скидання пароля (стандартні Django views)
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)