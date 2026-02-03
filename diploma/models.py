from django.db import models
from django.contrib.auth.models import User
import os
from uuid import uuid4

# --- ДОПОМІЖНІ ФУНКЦІЇ ---
def user_profile_photo_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return os.path.join('users', f'user_{instance.user.id}', 'profile_photos', filename)

def employee_photo_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return os.path.join('employees', filename)

# --- АДМІН ---
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_photo = models.ImageField(upload_to=user_profile_photo_path, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    bio = models.TextField(blank=True, max_length=500)
    def __str__(self): return f"Профіль: {self.user.username}"

# --- 1. КАРТОГРАФІЯ ---
class MineMap(models.Model):
    name = models.CharField(max_length=100, default="Основний горизонт", verbose_name="Назва карти")
    map_data = models.JSONField(default=dict, verbose_name="JSON карти")
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return self.name

class InfrastructureDevice(models.Model):
    uid = models.CharField(max_length=50, unique=True, verbose_name="ID на карті")
    wifi_bssid = models.CharField(max_length=17, unique=True, null=True, blank=True, verbose_name="MAC (BSSID)")
    map_location = models.ForeignKey(MineMap, on_delete=models.CASCADE, verbose_name="Карта")
    x = models.FloatField(verbose_name="X")
    y = models.FloatField(verbose_name="Y")
    is_active = models.BooleanField(default=True, verbose_name="Активний")
    def __str__(self): return f"{self.uid} [{self.wifi_bssid or 'NO MAC'}]"

# --- 2. ПЕРСОНАЛ ---
# --- 2. ПЕРСОНАЛ ---

class Employee(models.Model):
    # Тільки основні ролі для диплому
    POSITION_CHOICES = [
        ('GOV', 'Гірник очисного вибою (ГОВ)'),  # Основний робітник у забої
        ('PROH', 'Прохідник'),                   # Прокладає штреки
        ('EXPLODER', 'Майстер підривнки'),          # Керівник (ходить по дільницях)
        ('MASTER', 'Гірничий майстер'),          # Керівник (ходить по дільницях)
        ('ELECTRO', 'Гірничий електрослюсар'),   # Ремонтник (постійно переміщується)
        ('DISP', 'Диспетчер'),                   # Сидить на поверхні (для адмінки)
    ]

    STATUS_CHOICES = [
        ('OFF_SHIFT', 'Не на зміні'),
        ('OK', 'У шахті (Норма)'),
        ('WARNING', 'Попередження'),
        ('SOS', 'ТРИВОГА (SOS)'),
    ]

    first_name = models.CharField(max_length=50, verbose_name="Ім'я")
    last_name = models.CharField(max_length=50, verbose_name="Прізвище")
    patronymic = models.CharField(max_length=50, blank=True, verbose_name="По батькові")
    
    # Номер жетона (генерується автоматично)
    badge_number = models.CharField(max_length=30, unique=True, blank=True, verbose_name="№ Жетона")
    
    photo = models.ImageField(upload_to=employee_photo_path, null=True, blank=True, verbose_name="Фото")
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='GOV', verbose_name="Посада")
    
    safety_status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='OFF_SHIFT', verbose_name="Статус")
    last_update = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # АВТОМАТИЧНА ГЕНЕРАЦІЯ ЖЕТОНА
        if not self.badge_number:
            # 1. Ініціали (Прізвище + Ім'я)
            initials = f"{self.last_name[0]}{self.first_name[0]}".upper()
            # 2. Код посади
            pos_code = self.position 
            # 3. Порядковий номер
            count = Employee.objects.count() + 1
            # Результат: GOV-PI-001
            self.badge_number = f"{pos_code}-{initials}-{count:03d}" 
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.last_name} {self.first_name} (#{self.badge_number})"

# --- 3. ОБЛАДНАННЯ ---
class MinerDevice(models.Model):
    mac_address = models.CharField(max_length=17, unique=True, verbose_name="MAC (ESP32)")
    
    # Інвентарний номер теж авто-генеруємо
    inventory_number = models.CharField(max_length=50, unique=True, blank=True, verbose_name="Інв. номер")
    
    firmware_version = models.CharField(max_length=20, default="1.0.0", verbose_name="Прошивка")
    assigned_to = models.OneToOneField(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='device', verbose_name="Видано")
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.inventory_number:
            count = MinerDevice.objects.count() + 1
            self.inventory_number = f"LAMP-{count:04d}" # LAMP-0001
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.inventory_number} ({self.mac_address})"

# --- 4. ТЕЛЕМЕТРІЯ ---
class TelemetryLog(models.Model):
    device = models.ForeignKey(MinerDevice, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    connected_repeater = models.ForeignKey(InfrastructureDevice, on_delete=models.SET_NULL, null=True, blank=True)
    wifi_signal_strength = models.IntegerField(default=0, verbose_name="RSSI")
    temperature = models.FloatField(null=True)
    humidity = models.FloatField(null=True)
    gas_level = models.IntegerField(default=0, verbose_name="Gas PPM")
    battery_level = models.IntegerField(default=100)
    is_moving = models.BooleanField(default=True)
    is_sos = models.BooleanField(default=False)
    sos_reason = models.CharField(max_length=50, default='NONE')

    class Meta:
        ordering = ['-timestamp']
    def __str__(self): return f"Log {self.timestamp}"

# --- 5. ТРИВОГИ ---
class SecurityAlert(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    device = models.ForeignKey(MinerDevice, on_delete=models.CASCADE)
    location_label = models.CharField(max_length=100, verbose_name="Місце")
    reason = models.CharField(max_length=50, verbose_name="Причина")
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    def __str__(self): return f"SOS: {self.employee.last_name}"