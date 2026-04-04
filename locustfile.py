from locust import HttpUser, task, between
import random

class ESP32Device(HttpUser):
    # Кожна ESP32 відправляє дані приблизно раз на 4-6 секунд
    wait_time = between(4.0, 6.0)
    
    @task
    def send_telemetry(self):
        # Випадково обираємо 1 з 500 пристроїв
        device_id = random.randint(1, 500)
        mac = f"TEST-MAC-{device_id:04d}"
        ap = f"AP-TEST-{random.randint(1, 5)}"
        
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