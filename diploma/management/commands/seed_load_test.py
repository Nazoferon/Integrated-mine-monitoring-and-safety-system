from django.core.management.base import BaseCommand
from diploma.models import Employee, MinerDevice, InfrastructureDevice, MineMap

class Command(BaseCommand):
    help = 'Генерує 500 тестових працівників та пристроїв для навантажувального тестування.'

    def handle(self, *args, **options):
        self.stdout.write("Починаємо генерацію даних для навантажувального тесту...")
        
        mine_map, _ = MineMap.objects.get_or_create(name="Основний горизонт")
        
        # Створюємо 5 віртуальних репітерів
        for i in range(1, 6):
            InfrastructureDevice.objects.get_or_create(
                uid=f"AP-TEST-{i}",
                defaults={'map_location': mine_map, 'x': 0, 'y': 0, 'is_active': True}
            )
            
        # Створюємо 500 працівників та пристроїв (якщо їх ще немає)
        created_count = 0
        for i in range(1, 501):
            mac = f"TEST-MAC-{i:04d}"
            if not MinerDevice.objects.filter(mac_address=mac).exists():
                emp = Employee.objects.create(
                    first_name="Тест",
                    last_name=f"Шахтар-{i}",
                    position="GOV"
                )
                MinerDevice.objects.create(
                    mac_address=mac,
                    is_static=False,
                    assigned_to=emp,
                    is_active=True
                )
                created_count += 1
            if i % 100 == 0:
                self.stdout.write(f"Оброблено {i} пристроїв...")
                
        self.stdout.write(self.style.SUCCESS(f"Успішно додано {created_count} нових пристроїв!"))