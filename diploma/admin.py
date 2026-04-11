from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display, action
from .models import *

class MinerDeviceInline(TabularInline):
    model = MinerDevice
    can_delete = False
    fields = ('inventory_number', 'mac_address', 'is_active', 'firmware_version')
    readonly_fields = ('inventory_number', 'mac_address', 'firmware_version')
    extra = 0

@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ('user', 'phone_number')

@admin.register(MineMap)
class MineMapAdmin(ModelAdmin):
    list_display = ('name', 'updated_at')

@admin.register(InfrastructureDevice)
class InfrastructureDeviceAdmin(ModelAdmin):
    list_display = ('uid', 'wifi_bssid', 'map_location', 'show_active')
    list_filter = ('map_location',)
    search_fields = ('uid', 'wifi_bssid')

    @display(description="Статус", label=True)
    def show_active(self, obj):
        return ("Активний", "success") if obj.is_active else ("Вимкнено", "danger")

@admin.register(Employee)
class EmployeeAdmin(ModelAdmin):
    list_display = ('show_photo', 'last_name', 'first_name', 'badge_number', 'position', 'show_safety_status')
    list_filter = ('position', 'safety_status')
    search_fields = ('last_name', 'badge_number')
    # РОБИМО ЖЕТОН ТІЛЬКИ ДЛЯ ЧИТАННЯ
    readonly_fields = ('badge_number', 'last_update')
    inlines = [MinerDeviceInline]

    @display(description="Фото")
    def show_photo(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 36px; height: 36px; border-radius: 50%; object-fit: cover; border: 2px solid #4dabf7;" />', 
                obj.photo.url
            )
        return format_html('<div style="width: 36px; height: 36px; border-radius: 50%; background: #334155; display: flex; align-items: center; justify-content: center; color: #94a3b8; font-weight: bold; font-size: 14px; border: 2px solid transparent;">?</div>')

    @display(description="Статус безпеки", label=True)
    def show_safety_status(self, obj):
        colors = {'OFF_SHIFT': 'info', 'OK': 'success', 'WARNING': 'warning', 'SOS': 'danger'}
        return obj.get_safety_status_display(), colors.get(obj.safety_status, 'info')

@admin.register(MinerDevice)
class MinerDeviceAdmin(ModelAdmin):
    list_display = ('inventory_number', 'show_type', 'assigned_to', 'mac_address', 'show_active')
    list_filter = ('is_static', 'is_active')
    search_fields = ('inventory_number', 'mac_address')
    readonly_fields = ('inventory_number',)

    @display(description="Тип", label=True)
    def show_type(self, obj):
        return ("Стаціонарний", "info") if obj.is_static else ("Мобільний", "warning")

    @display(description="Статус", label=True)
    def show_active(self, obj):
        return ("Активний", "success") if obj.is_active else ("Вимкнено", "danger")
    
    fieldsets = (
        ('Основне', {
            'fields': ('mac_address', 'inventory_number', 'firmware_version', 'is_active')
        }),
        ('Режим роботи', {
            'fields': ('is_static', 'assigned_to'),
            'description': 'Якщо пристрій стаціонарний - працівника не вказуємо.'
        }),
        ('Координати (Тільки для стаціонарних)', {
            'fields': ('static_x', 'static_y'),
            'classes': ('collapse',), # Ховаємо, щоб не заважало
        }),
    )

@admin.register(TelemetryLog)
class TelemetryLogAdmin(ModelAdmin):
    list_display = ('timestamp', 'device', 'gas_level', 'show_sos')
    list_filter = ('is_sos', 'timestamp')
    date_hierarchy = 'timestamp'
    # Логи не можна змінювати, тільки дивитись
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False

    @display(description="Тривога", label=True)
    def show_sos(self, obj):
        return ("SOS", "danger") if obj.is_sos else ("Норма", "success")

@admin.register(SecurityAlert)
class SecurityAlertAdmin(ModelAdmin):
    list_display = ('created_at', 'employee', 'reason', 'show_status')
    list_filter = ('is_resolved', 'status', 'reason')
    date_hierarchy = 'created_at'
    # Завжди показувати найновіші тривоги зверху
    ordering = ('-created_at',)
    actions = ['mark_as_resolved']

    @display(description="Статус обробки", label=True)
    def show_status(self, obj):
        colors = {'NEW': 'danger', 'IN_PROGRESS': 'warning', 'WARNING': 'info', 'RESOLVED': 'success'}
        return obj.get_status_display(), colors.get(obj.status, 'default')

    @action(description="✅ Позначити вибрані як ВИРІШЕНІ")
    def mark_as_resolved(self, request, queryset):
        updated_count = queryset.update(
            status='RESOLVED', 
            is_resolved=True, 
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f"Успішно закрито {updated_count} інцидентів.", level="SUCCESS")

@admin.register(FirmwareUpdate)
class FirmwareUpdateAdmin(ModelAdmin):
    list_display = ('version', 'uploaded_at', 'show_active', 'description', 'binary_file')
    list_filter = ('is_active', 'uploaded_at')
    search_fields = ('version', 'description')
    date_hierarchy = 'uploaded_at'
    readonly_fields = ('uploaded_at',)
    filter_horizontal = ('target_devices',)

    @display(description="Статус", label=True)
    def show_active(self, obj):
        return ("Активна", "success") if obj.is_active else ("Неактивна", "danger")

    def save_model(self, request, obj, form, change):
        if obj.is_active:
            # Якщо ця прошивка позначається як активна, автоматично деактивуємо всі інші
            FirmwareUpdate.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)

@admin.register(OTALog)
class OTALogAdmin(ModelAdmin):
    list_display = ('timestamp', 'device', 'version', 'show_status')
    list_filter = ('status', 'timestamp')
    date_hierarchy = 'timestamp'
    search_fields = ('device__mac_address', 'device__inventory_number')
    readonly_fields = ('timestamp', 'device', 'version', 'status', 'message')
    # Логи не можна створювати або змінювати вручну
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False

    @display(description="Статус", label=True)
    def show_status(self, obj):
        return (obj.status, "success") if obj.status == "SUCCESS" else (obj.status, "danger")