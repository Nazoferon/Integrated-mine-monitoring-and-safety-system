from django.core.management.base import BaseCommand
from django.http import HttpRequest
from diploma.models import MinerDevice, InfrastructureDevice, SecurityAlert, TelemetryLog
from diploma.views import api_receive_telemetry
import time, json, os

class Command(BaseCommand):
    help = 'Запускає бойовий сценарій аварії для презентації'

    def send_telemetry(self, mac, ap, gas, temp, is_sos=False):
        """Допоміжна функція для імітації запиту від ESP32"""
        payload = {
            "mac_address": mac,
            "ap_uid": ap,
            "battery": 85,
            "gas_level": gas,
            "temperature": temp,
            "humidity": 55.0,
            "is_sos": is_sos,
            "is_moving": True,
            "rssi": -45
        }
        
        # Створюємо фейковий HTTP-запит і напряму викликаємо функцію API
        request = HttpRequest()
        request.method = 'POST'
        request._body = json.dumps(payload).encode('utf-8')
        request.META['CONTENT_TYPE'] = 'application/json'
        request.META['HTTP_X_API_KEY'] = os.environ.get("ESP32_API_KEY", "SecretMineKey2026")
        
        response = api_receive_telemetry(request)
        res_data = json.loads(response.content)
        
        if res_data.get('status') != 'success':
            self.stdout.write(self.style.ERROR(f"❌ Помилка API: {res_data.get('message')}"))

    def handle(self, *args, **options):
        # Знаходимо першого ліпшого працівника з пристроєм та активний репітер
        device = MinerDevice.objects.filter(is_static=False, assigned_to__isnull=False, is_active=True).first()
        ap = InfrastructureDevice.objects.filter(is_active=True).first()
        
        if not device or not ap:
            self.stdout.write(self.style.ERROR("Помилка: Немає активних пристроїв або репітерів у базі!"))
            return

        mac = device.mac_address
        ap_uid = ap.uid
        emp = device.assigned_to
        emp_name = f"{emp.first_name} {emp.last_name}"

        self.stdout.write(self.style.SUCCESS("\n=== БОЙОВИЙ СЦЕНАРІЙ ЗАПУЩЕНО ==="))
        self.stdout.write(f"📍 Ціль: {emp_name} (MAC: {mac}) на локації {ap_uid}")
        self.stdout.write("Відкрийте Дашборд або Карту у браузері!\n")

        try:
            # ФАЗА 1: Норма
            self.stdout.write("[Крок 1/3] Нормальна робота (10 секунд)...")
            for _ in range(2):
                self.send_telemetry(mac, ap_uid, gas=0.0, temp=20.0)
                time.sleep(5)

            # ФАЗА 2: Увага (Витік газу)
            self.stdout.write(self.style.WARNING("[Крок 2/3] Фіксуємо витік газу! Жовтий рівень (10 секунд)..."))
            for _ in range(2):
                self.send_telemetry(mac, ap_uid, gas=25.5, temp=24.0)
                time.sleep(5)

            # ФАЗА 3: Тривога
            self.stdout.write(self.style.ERROR("\n[Крок 3/3] КРИТИЧНИЙ РІВЕНЬ МЕТАНУ! ТРИВОГА!"))
            self.send_telemetry(mac, ap_uid, gas=65.0, temp=28.0)
            
            self.stdout.write(self.style.SUCCESS("\n🚨 Сирена активована! Покажіть дашборд комісії."))
            
            # Чекаємо, поки ви розкажете презентацію
            input("\n👉 Натисніть [ENTER], коли завершите демонстрацію, щоб очистити систему...")

        except KeyboardInterrupt:
            self.stdout.write("\nСценарій перервано.")

        # ФАЗА 4: Очищення
        self.stdout.write("\n🧹 Починаємо автоматичне очищення...")
        SecurityAlert.objects.filter(employee=emp).delete()
        TelemetryLog.objects.filter(device=device, gas_level__gte=25.0).delete() # Видаляємо тільки "аварійні" логи
        
        # Відправляємо фінальний нормальний пакет, щоб зняти всі статуси
        self.send_telemetry(mac, ap_uid, gas=0.0, temp=20.0)
        self.stdout.write(self.style.SUCCESS("✅ Очищення завершено! Система повернулась до норми."))