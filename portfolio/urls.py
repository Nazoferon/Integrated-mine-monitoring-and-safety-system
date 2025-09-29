from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Порожній шлях для домашньої сторінки
]