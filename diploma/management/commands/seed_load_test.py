from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Генерує 500 тестових працівників, пристроїв та 5 репітерів для навантажувального тестування.'

    def handle(self, *args, **options):
        from django.db import transaction
        from diploma.models import Employee, MinerDevice, InfrastructureDevice, MineMap

        self.stdout.write("Починаємо генерацію даних для навантажувального тесту...")

        with transaction.atomic():
            # Перевіряємо, чи існують реальні репітери на карті
            existing_aps = InfrastructureDevice.objects.filter(is_active=True).count()
            if existing_aps == 0:
                mine_map, _ = MineMap.objects.get_or_create(name="Основний горизонт")
                for i in range(1, 6):
                    InfrastructureDevice.objects.get_or_create(
                        uid=f"AP-TEST-{i}",
                        defaults={'map_location': mine_map, 'x': 0, 'y': 0, 'is_active': True}
                    )
                self.stdout.write("Створено 5 тестових репітерів (AP-TEST-...).")
            else:
                self.stdout.write(self.style.SUCCESS(f"✅ Знайдено {existing_aps} реальних репітерів на карті. Вони будуть використані для тесту."))

            # Створюємо 500 працівників та пристроїв (якщо їх ще немає)
            created_count = 0
            created_employees = 0
            for i in range(1, 501):
                mac = f"TEST-MAC-{i:04d}"
                if MinerDevice.objects.filter(mac_address=mac).exists():
                    continue

                emp, emp_created = Employee.objects.get_or_create(
                    badge_number=f"TEST-BADGE-{i:04d}",
                    defaults={
                        'first_name': "Тест",
                        'last_name': f"Симулятор-{i}",
                        'position': "GOV"
                    }
                )
                if emp_created:
                    created_employees += 1

                MinerDevice.objects.create(
                    mac_address=mac,
                    inventory_number=f"TEST-LAMP-{i:04d}",
                    is_static=False,
                    assigned_to=emp,
                    is_active=True
                )
                created_count += 1
                if i % 100 == 0:
                    self.stdout.write(f"Оброблено {i} пристроїв...")

            self.stdout.write(self.style.SUCCESS(f"Успішно створено {created_count} нових пристроїв та {created_employees} нових працівників."))
            self.stdout.write("Тепер ви можете запустити `locust -f locustfile.py`.")