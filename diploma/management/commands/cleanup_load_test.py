from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Видаляє тестових працівників та пристрої після навантажувального тестування.'

    def handle(self, *args, **options):
        from diploma.models import Employee, MinerDevice, InfrastructureDevice

        self.stdout.write("Починаємо видалення тестових даних...")
        
        # Видаляємо тестові репітери
        ap_deleted, _ = InfrastructureDevice.objects.filter(uid__startswith="AP-TEST-").delete()
        self.stdout.write(f"Видалено тестових репітерів: {ap_deleted}")
        
        # Видаляємо тестові пристрої (всі пов'язані логи телеметрії видаляться автоматично)
        dev_deleted, _ = MinerDevice.objects.filter(mac_address__startswith="TEST-MAC-").delete()
        self.stdout.write(f"Видалено тестових пристроїв: {dev_deleted}")
        
        # Видаляємо тестових працівників (всі їхні тривоги видаляться автоматично)
        emp_deleted, _ = Employee.objects.filter(first_name="Тест", last_name__startswith="Симулятор-").delete()
        self.stdout.write(f"Видалено тестових працівників: {emp_deleted}")
        
        self.stdout.write(self.style.SUCCESS("Очищення бази даних успішно завершено!"))