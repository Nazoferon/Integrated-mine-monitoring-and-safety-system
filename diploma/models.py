from django.db import models
from django.contrib.auth.models import User
import os
from uuid import uuid4
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- ДОПОМІЖНІ ФУНКЦІЇ ---

def user_profile_photo_path(instance, filename):
    """Шлях для збереження фото профілю"""
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return os.path.join('users', f'user_{instance.user.id}', 'profile_photos', filename)

def employee_photo_path(instance, filename):
    """Шлях для фото працівників (шахтарів)"""
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return os.path.join('employees', filename)

# --- КОРИСТУВАЧІ САЙТУ (АДМІНИ, ДИСПЕТЧЕРИ) ---

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_photo = models.ImageField(
        upload_to=user_profile_photo_path,
        blank=True,
        null=True,
        verbose_name="Фото профілю"
    )
    phone_number = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="Номер телефону"
    )
    bio = models.TextField(
        blank=True, 
        verbose_name="Біографія",
        max_length=500
    )

    def __str__(self):
        return f"Профіль {self.user.username}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'userprofile'):
        UserProfile.objects.create(user=instance)

# --- 1. КАРТОГРАФІЯ (ІМПОРТ З ПРОГРАМИ) ---

class MineMap(models.Model):
    name = models.CharField(max_length=100, default="Mine Map", verbose_name="Назва карти")
    
    # Сюди ви будете завантажувати JSON, згенерований вашим Python-застосунком.
    # Це дозволить сайту відмалювати карту для диспетчера.
    map_data = models.JSONField(default=dict, verbose_name="Дані карти (JSON з застосунку)")
    
    last_edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='edited_mine_maps')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# --- 2. ІНФРАСТРУКТУРА (ПРИСТРОЇ) ---

class InfrastructureDevice(models.Model):
    DEVICE_TYPES = [
        ('WIFI_REP', 'WiFi Repeater (ESP32)'),
        ('ENV_SENS', 'Environmental Sensor'),
        ('GATEWAY', 'Gateway'),
    ]
    STATUS_CHOICES = [
        ('ONLINE', 'В мережі'),
        ('OFFLINE', 'Не відповідає'),
        ('MAINTENANCE', 'На обслуговуванні'),
        ('ERROR', 'Помилка'),
    ]

    uid = models.CharField(max_length=50, unique=True, verbose_name="ID Пристрою (з MineCAD)")
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, default='WIFI_REP')
    
    # Прив'язка до карти
    map_location = models.ForeignKey(MineMap, on_delete=models.CASCADE, related_name='devices')
    
    # Координати дублюємо тут для швидкого доступу
    x = models.FloatField(default=0.0)
    y = models.FloatField(default=0.0)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OFFLINE')
    last_ping = models.DateTimeField(null=True, blank=True, verbose_name="Останній зв'язок")

    def __str__(self):
        return f"{self.uid} ({self.get_status_display()})"

# --- 3. ПЕРСОНАЛ (ШАХТАРІ) ---

class Employee(models.Model):
    """Фізичні працівники шахти"""
    # Якщо працівник має доступ до сайту, прив'язуємо User. Якщо це просто шахтар - поле пусте.
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_card')
    
    first_name = models.CharField(max_length=50, verbose_name="Ім'я")
    last_name = models.CharField(max_length=50, verbose_name="Прізвище")
    position = models.CharField(max_length=100, verbose_name="Посада")
    
    # RFID для трекінгу
    rfid_tag = models.CharField(max_length=50, unique=True, verbose_name="RFID/NFC Мітка")
    
    photo = models.ImageField(upload_to=employee_photo_path, null=True, blank=True, verbose_name="Фото")
    
    # Останні дані (кеш для швидкодії)
    last_seen = models.DateTimeField(null=True, blank=True)
    current_heart_rate = models.IntegerField(default=0)
    current_battery_level = models.FloatField(default=100.0)
    is_sos_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

# --- 4. ТЕЛЕМЕТРІЯ (ІСТОРІЯ) ---

class TelemetryLog(models.Model):
    """Історія руху та стану працівників"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Де був працівник
    x = models.FloatField()
    y = models.FloatField()
    
    heart_rate = models.IntegerField()
    body_temp = models.FloatField(null=True, blank=True)
    battery_level = models.FloatField()
    is_sos = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['employee', 'timestamp']),
        ]

# --- 5. БЕЗПЕКА (ТРИВОГИ) ---

class Alert(models.Model):
    SEVERITY = [
        ('INFO', 'Інформація'),
        ('WARNING', 'Попередження'),
        ('CRITICAL', 'КРИТИЧНО (SOS)'),
    ]
    
    created_at = models.DateTimeField(auto_now_add=True)
    severity = models.CharField(max_length=10, choices=SEVERITY)
    message = models.TextField(verbose_name="Повідомлення")
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True)
    device = models.ForeignKey(InfrastructureDevice, on_delete=models.CASCADE, null=True, blank=True)
    
    is_resolved = models.BooleanField(default=False, verbose_name="Вирішено")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"[{self.severity}] {self.message[:30]}"

# --- 6. ОБЛАДНАННЯ (СКЛАД) ---

class EquipmentType(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва типу")
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class EquipmentUnit(models.Model):
    STATUS_CHOICES = [
        ('OK', 'Робочий'),
        ('REPAIR', 'В ремонті'),
        ('LOST', 'Втрачено'),
    ]
    
    equipment_type = models.ForeignKey(EquipmentType, on_delete=models.CASCADE)
    serial_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OK')
    
    def __str__(self):
        return f"{self.equipment_type.name} #{self.serial_number}"

class EquipmentAssignment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    equipment = models.ForeignKey(EquipmentUnit, on_delete=models.CASCADE)
    issued_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.equipment} -> {self.employee}"