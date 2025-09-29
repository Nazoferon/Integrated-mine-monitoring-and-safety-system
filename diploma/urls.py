from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', views.diploma_home, name='diploma_home'),  # Головна сторінка дипломного сайту
    path('profile/', views.profile, name='profile'),  # Сторінка профілю
    path('mine_map/', views.mine_map, name='mine_map'),  # Сторінка з картою шахти
    path('download_map/', views.download_map, name='download_map'), # Завантаження карти шахти
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)