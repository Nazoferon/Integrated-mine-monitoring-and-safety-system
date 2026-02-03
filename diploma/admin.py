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
    list_display = ('inventory_number', 'mac_address', 'assigned_to', 'is_active')
    search_fields = ('inventory_number', 'mac_address')
    # ІНВЕНТАРНИЙ НОМЕР ТІЛЬКИ ДЛЯ ЧИТАННЯ
    readonly_fields = ('inventory_number',) 

@admin.register(TelemetryLog)
class TelemetryLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'device', 'gas_level', 'is_sos')
    list_filter = ('is_sos', 'timestamp')
    # Логи не можна змінювати, тільки дивитись
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False

@admin.register(SecurityAlert)
class SecurityAlertAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'employee', 'reason', 'is_resolved')
    list_filter = ('is_resolved', 'reason')