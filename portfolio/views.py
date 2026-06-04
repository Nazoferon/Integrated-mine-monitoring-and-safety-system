from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Category, Project

def home(request):
    categories = Category.objects.all()
    # Завантажуємо всі проєкти
    projects = Project.objects.select_related('category').all()
    
    return render(request, 'portfolio/index.html', {
        'categories': categories,
        'projects': projects
    })

def privacy_policy(request):
    return render(request, 'portfolio/privacy.html')
