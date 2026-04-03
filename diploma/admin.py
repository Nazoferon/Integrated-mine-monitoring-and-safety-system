from django.contrib import admin
from .models import *

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number')

@admin.register(MineMap)
class MineMapAdmin(admin.ModelAdmin):
    list_display = ('name', 'updated_at')

@admin.register(InfrastructureDevice)
class InfrastructureDeviceAdmin(admin.ModelAdmin):
    list_display = ('uid', 'wifi_bssid', 'map_location', 'is_active')
    list_filter = ('map_location',)
    search_fields = ('uid', 'wifi_bssid')

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'badge_number', 'position', 'safety_status')
    list_filter = ('position', 'safety_status')
    search_fields = ('last_name', 'badge_number')
    # РОБИМО ЖЕТОН ТІЛЬКИ ДЛЯ ЧИТАННЯ
    readonly_fields = ('badge_number', 'last_update') 

@admin.register(MinerDevice)
class MinerDeviceAdmin(admin.ModelAdmin):
    list_display = ('inventory_number', 'is_static', 'assigned_to', 'mac_address', 'is_active')
    list_filter = ('is_static', 'is_active')
    search_fields = ('inventory_number', 'mac_address')
    readonly_fields = ('inventory_number',)
    
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
class TelemetryLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'device', 'gas_level', 'is_sos')
    list_filter = ('is_sos', 'timestamp')
    date_hierarchy = 'timestamp'
    # Логи не можна змінювати, тільки дивитись
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False

@admin.register(SecurityAlert)
class SecurityAlertAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'employee', 'reason', 'is_resolved')
    list_filter = ('is_resolved', 'reason')
    date_hierarchy = 'created_at'
    # Завжди показувати найновіші тривоги зверху
    ordering = ('-created_at',)

@admin.register(FirmwareUpdate)
class FirmwareUpdateAdmin(admin.ModelAdmin):
    list_display = ('version', 'uploaded_at', 'is_active', 'description', 'binary_file')
    list_filter = ('is_active', 'uploaded_at')
    search_fields = ('version', 'description')
    date_hierarchy = 'uploaded_at'
    readonly_fields = ('uploaded_at',)
    filter_horizontal = ('target_devices',)

    def save_model(self, request, obj, form, change):
        if obj.is_active:
            # Якщо ця прошивка позначається як активна, автоматично деактивуємо всі інші
            FirmwareUpdate.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)

@admin.register(OTALog)
class OTALogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'device', 'version', 'status')
    list_filter = ('status', 'timestamp')
    date_hierarchy = 'timestamp'
    search_fields = ('device__mac_address', 'device__inventory_number')
    readonly_fields = ('timestamp', 'device', 'version', 'status', 'message')
    # Логи не можна створювати або змінювати вручну
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False