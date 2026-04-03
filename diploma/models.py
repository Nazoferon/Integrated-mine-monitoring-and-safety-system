'''
Я передбачив навантаження на базу даних: для таблиці телеметрії створені B-Tree індекси 
по ключових полях і складений індекс 'Пристрій + Час'. У реальному впровадженні 
передбачається використання Cron-задачі, яка щоночі буде видаляти або архівувати логи, 
старші за 30 днів, залишаючи лише записи про інциденти
'''

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import os
from django.core.validators import RegexValidator
from uuid import uuid4
import math

# --- ДОПОМІЖНІ ФУНКЦІЇ ---
def user_profile_photo_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return os.path.join('users', f'user_{instance.user.id}', 'profile_photos', filename)

def employee_photo_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return os.path.join('employees', filename)

def dist_to_segment(px, py, x1, y1, x2, y2):
    """Обчислює найкоротшу відстань від точки (px, py) до відрізка [(x1, y1), (x2, y2)]."""
    l2 = (x1 - x2)**2 + (y1 - y2)**2
    if l2 == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2
    t = max(0, min(1, t))
    return math.hypot(px - (x1 + t * (x2 - x1)), py - (y1 + t * (y2 - y1)))

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
    wifi_ssid = models.CharField(max_length=32, db_index=True, verbose_name="Назва мережі (SSID)", help_text="Саме цю назву шукатиме пристрій в ефірі.", default="", blank=True)
    wifi_bssid = models.CharField(max_length=17, unique=True, null=True, blank=True, verbose_name="MAC (BSSID)")
    wifi_password = models.CharField(max_length=64, blank=True, verbose_name="Пароль мережі (якщо є)")
    map_location = models.ForeignKey(MineMap, on_delete=models.CASCADE, verbose_name="Карта")
    x = models.FloatField(verbose_name="X")
    y = models.FloatField(verbose_name="Y")
    is_active = models.BooleanField(default=True, verbose_name="Активний")

    @property
    def location_in_mine(self):
        """Повертає назву штреку або 'Руддвір', де знаходиться пристрій."""
        if self.map_location and self.map_location.map_data:
            # 1. Перевірка на явну вкладеність у JSON (швидкий та надійний спосіб)
            for t in self.map_location.map_data.get('tunnels', []):
                if isinstance(t.get('devices'), list) and any(str(d.get('id')) == str(self.uid) for d in t.get('devices')):
                    return t.get('name')

            # 2. Якщо не знайдено, перевірка за геометричною близькістю до лінії штреку
            # (для пристроїв, що не вкладені в JSON, а розміщені за координатами)
            closest_tunnel = None
            min_dist = float('inf')
            dev_x, dev_y = self.x, self.y

            for t in self.map_location.map_data.get('tunnels', []):
                dist = dist_to_segment(dev_x, dev_y, t.get('x1', 0), t.get('y1', 0), t.get('x2', 0), t.get('y2', 0))
                if dist < min_dist:
                    min_dist = dist
                    closest_tunnel = t

            # Якщо пристрій знаходиться дуже близько до лінії (напр. < 2 одиниць на карті)
            if closest_tunnel and min_dist < 2:
                return closest_tunnel.get('name')

        return "Руддвір / База"

    def __str__(self): return f"{self.uid} [{self.wifi_bssid or 'NO MAC'}]"

# --- 2. ПЕРСОНАЛ ---

# Валідатор для перевірки розміру файлу ДО завантаження (щоб не вантажили 100МБ)
def validate_image_size(image):
    file_size = image.size
    limit_mb = 5
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Максимальний розмір файлу {limit_mb} MB")

# Manager для Employee з оптимізацією запитів для personnel_list
class EmployeeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('device')

    def all_with_device_status(self):
        # Оптимізація для вибірки device та його is_active
        return self.get_queryset().select_related('device')

class Employee(models.Model):
    # Тільки основні ролі для диплому
    POSITION_CHOICES = [
        ('GOV', 'Гірник очисного вибою (ГОВ)'),  # Основний робітник у забої
        ('PROH', 'Прохідник'),                   # Прокладає штреки
        ('EXPLODER', 'Майстер підривник'),          # Керівник (ходить по дільницях)
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

    last_name = models.CharField(max_length=50, verbose_name="Прізвище")
    first_name = models.CharField(max_length=50, verbose_name="Ім'я")
    patronymic = models.CharField(max_length=50, blank=True, verbose_name="По батькові")
    
    # Номер жетона (генерується автоматично)
    badge_number = models.CharField(max_length=30, unique=True, blank=True, verbose_name="№ Жетона")
    
    objects = EmployeeManager()

    # ДОДАЄМО ВАЛІДАТОР І HELP TEXT
    photo = models.ImageField(
        upload_to=employee_photo_path, 
        null=True, 
        blank=True, 
        verbose_name="Фото",
        validators=[validate_image_size], # Перевірка на 5 МБ
        help_text="Макс. розмір 5 МБ. Фото буде автоматично стиснуто."
    )

    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='GOV', verbose_name="Посада")
    
    safety_status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='OFF_SHIFT', verbose_name="Статус")
    last_update = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.badge_number:
            # Словник для транслітерації ініціалів
            translit = {'А':'A', 'Б':'B', 'В':'V', 'Г':'G', 'Ґ':'G', 'Д':'D', 'Е':'E', 'Є':'YE', 
                        'Ж':'ZH', 'З':'Z', 'И':'Y', 'І':'I', 'Ї':'YI', 'Й':'Y', 'К':'K', 'Л':'L', 
                        'М':'M', 'Н':'N', 'О':'O', 'П':'P', 'Р':'R', 'С':'S', 'Т':'T', 'У':'U', 
                        'Ф':'F', 'Х':'KH', 'Ц':'TS', 'Ч':'CH', 'Ш':'SH', 'Щ':'SHCH', 'Ю':'YU', 'Я':'YA'}
            
            last_initial = self.last_name[0].upper() if self.last_name else ''
            first_initial = self.first_name[0].upper() if self.first_name else ''
            
            # Переводимо в латиницю
            lat_last = translit.get(last_initial, last_initial)
            lat_first = translit.get(first_initial, first_initial)
            
            # Отримуємо наступний ID (спрощений варіант)
            next_id = Employee.objects.count() + 1
            
            # Формуємо жетон: EXPLODER-GN-001
            self.badge_number = f"{self.position}-{lat_last}{lat_first}-{next_id:03d}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.last_name} {self.first_name} (#{self.badge_number})"

# --- 3. ОБЛАДНАННЯ ---

class MinerDevice(models.Model):
    mac_address = models.CharField(max_length=17, unique=True, verbose_name="MAC (ESP32)")
    inventory_number = models.CharField(max_length=50, unique=True, blank=True, verbose_name="Інв. номер")
    firmware_version = models.CharField(max_length=20, default="1.0.0", verbose_name="Прошивка")
    
    is_static = models.BooleanField(default=False, verbose_name="Стаціонарний (на стіні)?")
    static_x = models.FloatField(null=True, blank=True, verbose_name="X (якщо стаціонарний)")
    static_y = models.FloatField(null=True, blank=True, verbose_name="Y (якщо стаціонарний)")

    assigned_to = models.OneToOneField(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='device', verbose_name="Видано (кому)"
    )
    is_active = models.BooleanField(default=True)

    # --- 2. ЛОГІКА ПЕРЕВІРКИ (VALIDATION) ---
    def clean(self):
        # Перевірка 1: Якщо НЕ стаціонарний -> Працівник ОБОВ'ЯЗКОВИЙ
        if not self.is_static and self.assigned_to is None:
            raise ValidationError({
                'assigned_to': "Мобільна коногонка мусить бути видана працівнику! Оберіть працівника або позначте як 'Стаціонарний'."
            })

        # Перевірка 2: Якщо стаціонарний -> Працівник ЗАБОРОНЕНИЙ
        if self.is_static and self.assigned_to is not None:
            raise ValidationError({
                'assigned_to': "Стаціонарний датчик не може бути прив'язаний до людини. Очистіть це поле."
            })

    def save(self, *args, **kwargs):
        # Авто-генерація номера
        if not self.inventory_number:
            count = MinerDevice.objects.count() + 1
            prefix = "SENS" if self.is_static else "LAMP"
            self.inventory_number = f"{prefix}-{count:04d}"
            
        # Запускаємо перевірку clean() перед записом у БД
        self.clean()
        
        super().save(*args, **kwargs)

    def __str__(self):
        type_label = "📍СТІНА" if self.is_static else "👤КАСКА"
        return f"{self.inventory_number} [{type_label}]"

# --- 4. ТЕЛЕМЕТРІЯ ---
class TelemetryLog(models.Model):
    device = models.ForeignKey(MinerDevice, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    connected_repeater = models.ForeignKey(InfrastructureDevice, on_delete=models.SET_NULL, null=True, blank=True)
    wifi_signal_strength = models.IntegerField(default=0, verbose_name="RSSI")
    temperature = models.FloatField(null=True)
    humidity = models.FloatField(null=True)
    gas_level = models.FloatField(default=0, verbose_name="Gas % LEL")
    battery_level = models.IntegerField(default=100)
    is_moving = models.BooleanField(default=True)
    is_sos = models.BooleanField(default=False, db_index=True)
    sos_reason = models.CharField(max_length=255, default='NONE')

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            # Складений індекс для надшвидкого пошуку "останнього логу конкретного пристрою"
            models.Index(fields=['device', '-timestamp']),
        ]
        
    def __str__(self): 
        # Відформатований час: "Лог 2026-04-01 11:58:54"
        return f"Лог {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

# --- 5. ТРИВОГИ ---
class SecurityAlert(models.Model):
    ALERT_STATUS_CHOICES = [
        ('NEW', '🔴 Нова (Необроблена)'),
        ('IN_PROGRESS', '🟡 В процесі порятунку'),
        ('WARNING', '🟠 Попередження (Системне)'),
        ('RESOLVED', '🟢 Вирішено (Безпечно)'),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    device = models.ForeignKey(MinerDevice, on_delete=models.CASCADE)
    
    # --- НОВЕ ПОЛЕ ДЛЯ РЕПІТЕРА ---
    connected_repeater = models.ForeignKey(
        InfrastructureDevice, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Найближчий репітер"
    )
    
    location_label = models.CharField(max_length=100, verbose_name="Місце", blank=True)
    reason = models.CharField(max_length=255, verbose_name="Причина")
    
    status = models.CharField(max_length=20, choices=ALERT_STATUS_CHOICES, default='NEW', verbose_name="Статус обробки")
    rescue_notes = models.TextField(blank=True, verbose_name="Нотатки диспетчера / Вжиті заходи")
    
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self): return f"SOS: {self.employee.last_name} ({self.status})"

# --- 6. OTA ОНОВЛЕННЯ ПРОШИВКИ ---
class FirmwareUpdate(models.Model):
    version = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Версія прошивки (напр. 1.0.1)",
        validators=[
            RegexValidator(regex=r'^\d+\.\d+\.\d+$', message='Версія має бути у форматі X.Y.Z (тільки цифри та крапки, наприклад: 1.0.0 або 2.1.15)')
        ]
    )
    binary_file = models.FileField(upload_to='firmwares_esp/', verbose_name="Файл прошивки (.bin)")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата завантаження")
    is_active = models.BooleanField(default=True, verbose_name="Активна (роздавати пристроям)")
    description = models.TextField(blank=True, verbose_name="Опис / Причина оновлення")
    target_devices = models.ManyToManyField(MinerDevice, blank=True, verbose_name="Цільові пристрої", help_text="Якщо вибрано пристрої, оновлення отримають ТІЛЬКИ вони. Якщо пусто — отримають усі.")

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Оновлення прошивки"
        verbose_name_plural = "Оновлення прошивок"

    def __str__(self):
        return f"Прошивка v{self.version}"

# --- 7. ЛОГУВАННЯ OTA ОНОВЛЕНЬ ---
class OTALog(models.Model):
    device = models.ForeignKey(MinerDevice, on_delete=models.CASCADE, related_name='ota_logs', verbose_name="Пристрій")
    version = models.CharField(max_length=20, verbose_name="Версія, що встановлювалась")
    status = models.CharField(max_length=20, verbose_name="Статус")  # SUCCESS або FAILED
    message = models.TextField(blank=True, verbose_name="Помилка/Деталі")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Час спроби")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Лог оновлення (OTA)"
        verbose_name_plural = "Логи оновлень (OTA)"

    def __str__(self):
        return f"{self.device.inventory_number} -> v{self.version} [{self.status}]"