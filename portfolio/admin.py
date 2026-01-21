from django.contrib import admin
from .models import Category, Project
from django.utils.html import format_html

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order', 'icon_preview')
    list_editable = ('order',)  # Можна змінювати порядок прямо в списку
    prepopulated_fields = {'slug': ('name',)}

    def icon_preview(self, obj):
        return format_html('<i class="{}" style="font-size: 20px;"></i>', obj.icon_class)
    icon_preview.short_description = "Іконка"

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_completed', 'image_preview')
    list_filter = ('category', 'is_completed')
    search_fields = ('title', 'description', 'tech_stack')
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('category', 'title', 'image', 'is_completed')
        }),
        ('Деталі', {
            'fields': ('description', 'tech_stack')
        }),
        ('Посилання', {
            'fields': ('github_link', 'demo_link')
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: auto;" />', obj.image.url)
        return "Немає фото"
    image_preview.short_description = "Фото"