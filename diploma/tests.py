'''
Мій бекенд покритий Unit-тестами. Система автоматично перевіряє критичні вузли: 
генерацію тривог при перевищенні газу, обробку кнопок SOS та ігнорування хибних 
спрацювань (наприклад, розрядженої батареї наприкінці зміни, коли гірник вже біля 
виходу). Будь-яка зміна в коді не зламає цю логіку, оскільки перед деплоєм проганяються тести.
'''

from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
import json
import os
from diploma.models import Employee, MinerDevice, InfrastructureDevice, SecurityAlert, MineMap

class DiplomaModelsTest(TestCase):
    """Тестування бізнес-логіки на рівні моделей."""
    
    def test_employee_badge_generation(self):
        """Перевірка автогенерації номера жетона для працівника."""
        emp = Employee.objects.create(
            first_name="Іван",
            last_name="Іванов",
            position="GOV"
        )
        # Іванов Іван (GOV) -> Транслітерація має дати I I -> GOV-II-001
        self.assertTrue(emp.badge_number.startswith("GOV-II-"))
        self.assertIsNotNone(emp.badge_number)

    def test_miner_device_validation(self):
        """Перевірка валідації обладнання."""
        emp = Employee.objects.create(first_name="Петро", last_name="Петров")
        
        # 1. Мобільна коногонка без працівника (має бути помилка)
        mobile_device = MinerDevice(mac_address="00:11:22:33:44:55", is_static=False, assigned_to=None)
        with self.assertRaises(ValidationError):
            mobile_device.clean()
            
        # 2. Стаціонарний датчик з працівником (має бути помилка)
        static_device = MinerDevice(mac_address="AA:BB:CC:DD:EE:FF", is_static=True, assigned_to=emp)
        with self.assertRaises(ValidationError):
            static_device.clean()
            
        # 3. Правильна конфігурація (не повинно бути помилки)
        valid_device = MinerDevice(mac_address="11:22:33:44:55:66", is_static=False, assigned_to=emp)
        try:
            valid_device.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly!")


class TelemetryAPITest(TestCase):
    """Тестування API прийому даних від ESP32."""
    
    def setUp(self):
        self.client = Client()
        self.mine_map = MineMap.objects.create(name="Тестова карта")
        
        self.ap = InfrastructureDevice.objects.create(
            uid="AP-TEST",
            wifi_bssid="11:22:33:44:55:66",
            x=0, y=0,
            map_location=self.mine_map
        )
        
        self.emp = Employee.objects.create(first_name="Олег", last_name="Сидоров")
        self.device = MinerDevice.objects.create(
            mac_address="AA:BB:CC:DD:EE:FF",
            is_static=False,
            assigned_to=self.emp
        )

    def test_api_key_protection_missing(self):
        """Перевірка захисту API: відмова без ключа."""
        response = self.client.post(
            reverse('api_telemetry'),
            data=json.dumps({"mac_address": self.device.mac_address}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Unauthorized", response.json().get('error', ''))

    def test_api_key_protection_invalid(self):
        """Перевірка захисту API: відмова з неправильним ключем."""
        response = self.client.post(
            reverse('api_telemetry'),
            data=json.dumps({"mac_address": self.device.mac_address}),
            content_type="application/json",
            HTTP_X_API_KEY="WRONG_KEY_123"
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn("Unauthorized", response.json().get('error', ''))

    def test_api_sos_alert_creation(self):
        """Перевірка створення тривоги при отриманні SOS сигналу."""
        payload = {
            "mac_address": self.device.mac_address,
            "ap_uid": self.ap.uid,
            "battery": 80,
            "gas_level": 0,
            "is_sos": True,
            "reason": "MANUAL SOS"
        }
        
        response = self.client.post(
            reverse('api_telemetry'),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=os.environ.get("ESP32_API_KEY", "SecretMineKey2026")
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Перевіряємо чи створилась активна тривога
        alert_exists = SecurityAlert.objects.filter(employee=self.emp, is_resolved=False).exists()
        self.assertTrue(alert_exists)
        
        # Перевіряємо чи змінився статус працівника
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.safety_status, "SOS")

    def test_api_high_gas_alert(self):
        """Перевірка автоматичного створення тривоги при критичному рівні метану."""
        payload = {
            "mac_address": self.device.mac_address,
            "ap_uid": self.ap.uid,
            "battery": 90,
            "gas_level": 55.0,  # Критичний рівень (>50)
            "is_sos": False
        }
        
        self.client.post(
            reverse('api_telemetry'),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_API_KEY=os.environ.get("ESP32_API_KEY", "SecretMineKey2026")
        )
        
        # Перевіряємо тривогу та її причину
        alert = SecurityAlert.objects.filter(employee=self.emp, is_resolved=False).first()
        self.assertIsNotNone(alert)
        self.assertIn("КРИТИЧНИЙ рівень CH4", alert.reason)
        
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.safety_status, "SOS")

    def test_low_battery_alert_ignored_at_base(self):
        """Перевірка ігнорування тривоги низького заряду, якщо шахтар на базі (AP-MAIN)."""
        ap_main = InfrastructureDevice.objects.create(uid="AP-MAIN", map_location=self.mine_map, x=0, y=0)
        
        payload = {
            "mac_address": self.device.mac_address,
            "ap_uid": "AP-MAIN",
            "battery": 5,  # Критично низький заряд
            "gas_level": 0,
            "is_sos": False
        }
        
        self.client.post(
            reverse('api_telemetry'), 
            data=json.dumps(payload), 
            content_type="application/json",
            HTTP_X_API_KEY=os.environ.get("ESP32_API_KEY", "SecretMineKey2026")
        )
        
        # Оскільки працівник біля AP-MAIN, система не повинна створювати тривогу
        alert_exists = SecurityAlert.objects.filter(employee=self.emp, is_resolved=False).exists()
        self.assertFalse(alert_exists)
