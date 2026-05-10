from locust import HttpUser, task, between
import random
import os
import django

# Ініціалізуємо Django для доступу до реальних репітерів з БД
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()
from diploma.models import InfrastructureDevice, MinerDevice

# Отримуємо всі активні репітери (щоб Locust кидав телеметрію на реальну карту)
ACTIVE_APS = list(InfrastructureDevice.objects.filter(is_active=True).values_list('uid', flat=True))
if not ACTIVE_APS:
    ACTIVE_APS = [f"AP-TEST-{i}" for i in range(1, 6)]

# Отримуємо всі реальні MAC-адреси пристроїв з БД (мобільні, які видані шахтарям)
ACTIVE_MACS = list(MinerDevice.objects.filter(is_static=False, assigned_to__isnull=False).values_list('mac_address', flat=True))
if not ACTIVE_MACS:
    ACTIVE_MACS = ["TEST-MAC-0001"] # fallback

# ВАШ API КЛЮЧ 
API_KEY = "SecretMineKey2026"

class ESP32Device(HttpUser):
    # Кожна ESP32 відправляє дані приблизно раз на 4-6 секунд
    wait_time = between(4.0, 6.0)
    
    def on_start(self):
        # Додаємо API ключ у правильний заголовок X-API-Key
        self.client.headers.update({
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        })

    @task
    def send_telemetry(self):
        # Випадково обираємо один з існуючих пристроїв у базі
        mac = random.choice(ACTIVE_MACS)
        ap = random.choice(ACTIVE_APS)

        payload = {
            "mac_address": mac,
            "ap_uid": ap,
            "battery": random.randint(50, 100),
            "gas_level": round(random.uniform(0.0, 5.0), 2),
            "temperature": round(random.uniform(18.0, 24.0), 1),
            "humidity": round(random.uniform(40.0, 60.0), 1),
            "is_sos": False,
            "is_moving": True,
            "rssi": random.randint(-80, -30)
        }
        # Відправляємо POST запит і виводимо помилку, якщо вона є
        with self.client.post("/diploma/test/telemetry/", json=payload, catch_response=True) as response:
            if response.status_code != 200:
                print(f"ПОМИЛКА ТЕЛЕМЕТРІЇ: Код {response.status_code}, Відповідь: {response.text}")
                response.failure(f"Помилка {response.status_code}")

class WebDashboardUser(HttpUser):
    # Імітуємо відкриті вкладки браузера диспетчерів (оновлення кожні 5 сек)
    wait_time = between(4.5, 5.5)
    
    def on_start(self):
        # Додаємо API ключ у правильний заголовок X-API-Key
        self.client.headers.update({
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        })

    @task
    def get_dashboard_stats(self):
        self.client.get("/diploma/test/dashboard/")
