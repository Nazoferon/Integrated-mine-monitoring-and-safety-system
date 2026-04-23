from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views 
from django.conf import settings
from django.conf.urls.static import static
from django.urls import reverse_lazy
from django.urls import path
from diploma.auth_forms import TurnstileAuthenticationForm
import os

from diploma import views as diploma_views
from portfolio.views import home

urlpatterns = [
    path('secret-mine-control/', admin.site.urls),
    path('', include('portfolio.urls')),  # Домашня сторінка — portfolio
    path('diploma/', include('diploma.urls')),

    # Авторизація
    path('login/', auth_views.LoginView.as_view(
        template_name='diploma/login.html',
        form_class=TurnstileAuthenticationForm,
        extra_context={'turnstile_site_key': os.getenv('TURNSTILE_SITE_KEY', '1x00000000000000000000AA')}
    ), name='login'),
    path('logout/', diploma_views.custom_logout_view, name='logout'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
