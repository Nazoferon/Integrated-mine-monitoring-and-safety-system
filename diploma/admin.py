from django.contrib import admin

from .models import (
    UserProfile, MineMap, InfrastructureDevice, 
    Employee, TelemetryLog, Alert, 
    EquipmentType, EquipmentUnit, EquipmentAssignment
)

# --- ПРОФІЛЬ КОРИСТУВАЧА ---
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number')
    search_fields = ('user__username', 'phone_number')

# --- КАРТОГРАФІЯ ---
@admin.register(MineMap)
class MineMapAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at', 'last_edited_by')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(InfrastructureDevice)
class InfrastructureDeviceAdmin(admin.ModelAdmin):
    list_display = ('uid', 'device_type', 'status', 'map_location', 'last_ping')
    list_filter = ('device_type', 'status', 'map_location')
    search_fields = ('uid', 'ip_address')
    # Робимо гарні кольори для статусу (зелений/червоний)
    def get_status_display_color(self, obj):
        return obj.get_status_display()
    get_status_display_color.short_description = 'Статус'

# --- ПЕРСОНАЛ ---
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'position', 'rfid_tag', 'is_sos_active')
    list_filter = ('position', 'is_sos_active')
    search_fields = ('last_name', 'first_name', 'rfid_tag')
    ordering = ('last_name',)

# --- ТЕЛЕМЕТРІЯ (Тільки перегляд, бо записів буде багато) ---
@admin.register(TelemetryLog)
class TelemetryLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'employee', 'heart_rate', 'battery_level', 'is_sos')
    list_filter = ('timestamp', 'is_sos', 'employee')
    ordering = ('-timestamp',)
    
    # Вимикаємо можливість додавати/змінювати логи вручну, щоб зберегти цілісність історії
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False

# --- БЕЗПЕКА ---
@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'severity', 'message', 'is_resolved', 'resolved_by')
    list_filter = ('severity', 'is_resolved', 'created_at')
    search_fields = ('message',)
    ordering = ('-created_at',)

# --- ОБЛАДНАННЯ ---
@admin.register(EquipmentType)
class EquipmentTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(EquipmentUnit)
class EquipmentUnitAdmin(admin.ModelAdmin):
    list_display = ('equipment_type', 'serial_number', 'status')
    list_filter = ('status', 'equipment_type')
    search_fields = ('serial_number',)

@admin.register(EquipmentAssignment)
class EquipmentAssignmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'equipment', 'issued_at', 'returned_at')
    list_filter = ('issued_at', 'returned_at')
    autocomplete_fields = ['employee', 'equipment'] # Зручний пошук, якщо багато записів