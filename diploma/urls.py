from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views
from diploma.auth_forms import TurnstilePasswordResetForm
import os

class CustomPasswordResetView(auth_views.PasswordResetView):
    form_class = TurnstilePasswordResetForm
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request # Прокидаємо request у форму для Turnstile
        return kwargs

urlpatterns = [
    # Головні сторінки
    path('', views.diploma_home, name='diploma_home'),
    path('profile/', views.profile, name='profile'),
    path('personnel/', views.personnel_list, name='personnel'),
    path('equipment/', views.equipment_list, name='equipment'),
    path('reports/', views.reports_view, name='reports'),
    # Симулятор для тестування руху працівників на карті
    path('simulator/', views.simulator_view, name='simulator'),
    # Завантаження архівів звітів
    path('reports/download/<str:filename>/', views.download_archive, name='download_archive'),

    
    # Карта та інструменти
    path('mine_map/', views.mine_map, name='mine_map'),
    path('download_map/', views.download_map, name='download_map'),
    
    # Інциденти та Телеметрія
    path('alert/<int:alert_id>/', views.alert_detail, name='alert_detail'),
    
    # API ендпоінти
    path('api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('api/upload-map/', views.upload_map_api, name='upload_map_api'),
    path('api/reports-data/', views.reports_data_api, name='reports_data_api'),
    path('alert/<int:alert_id>/api/', views.alert_telemetry_api, name='alert_telemetry_api'),
    path('api/equipment-telemetry/', views.equipment_telemetry_api, name='equipment_telemetry_api'),
    path('api/equipment-list/', views.equipment_list_api, name='equipment_list_api'),
    path('api/personnel-list/', views.personnel_list_api, name='personnel_list_api'),
    path('personnel-status-api/', views.personnel_status_api, name='personnel_status_api'),
    
    # API для симулятора
    path('api/telemetry/', views.api_receive_telemetry, name='api_telemetry'),
    path('api/miners/', views.api_active_miners, name='api_miners'),
    path('api/wifi-networks/', views.api_get_wifi_networks, name='api_wifi_networks'),
    path('api/ota/check/', views.api_ota_check, name='api_ota_check'),
    path('api/ota/log/', views.api_ota_log, name='api_ota_log'),

    # Скидання пароля (стандартні Django views)
    path('password_reset/', CustomPasswordResetView.as_view(
        template_name='diploma/auth/password_reset_form.html',
        html_email_template_name='diploma/auth/password_reset_email.html',
        email_template_name='diploma/auth/password_reset_email.txt',
        subject_template_name='diploma/auth/password_reset_subject.txt',
        extra_context={'turnstile_site_key': os.getenv('TURNSTILE_SITE_KEY', '1x00000000000000000000AA')}
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='diploma/auth/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='diploma/auth/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='diploma/auth/password_reset_complete.html'), name='password_reset_complete'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)