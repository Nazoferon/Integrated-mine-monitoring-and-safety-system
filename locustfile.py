from locust import HttpUser, task, between
import random
import os
import django

# Ініціалізуємо Django для доступу до реальних репітерів з БД
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()
from diploma.models import InfrastructureDevice

# Отримуємо всі активні репітери (щоб Locust кидав телеметрію на реальну карту)
ACTIVE_APS = list(InfrastructureDevice.objects.filter(is_active=True).values_list('uid', flat=True))
if not ACTIVE_APS:
    ACTIVE_APS = [f"AP-TEST-{i}" for i in range(1, 6)]

class ESP32Device(HttpUser):
    # Кожна ESP32 відправляє дані приблизно раз на 4-6 секунд
    wait_time = between(4.0, 6.0)
    
    @task
    def send_telemetry(self):
        # Випадково обираємо 1 з 500 пристроїв
        device_id = random.randint(1, 500)
        mac = f"TEST-MAC-{device_id:04d}"
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
        # Відправляємо POST запит на наш API
        self.client.post("/diploma/api/telemetry/", json=payload)

class WebDashboardUser(HttpUser):
    # Імітуємо відкриті вкладки браузера диспетчерів (оновлення кожні 5 сек)
    wait_time = between(4.5, 5.5)
    
    @task
    def get_dashboard_stats(self):
        self.client.get("/diploma/api/dashboard-stats/")