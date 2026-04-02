from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from diploma.models import MinerDevice, TelemetryLog

class Command(BaseCommand):
    help = 'Checks for inactive devices and sets their status to is_active=False'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=60,  # За замовчуванням 60 хвилин
            help='Set the inactivity timeout in minutes for devices.'
        )

    def handle(self, *args, **options):
        timeout_minutes = options['timeout']
        self.stdout.write(f"Starting check for devices inactive for more than {timeout_minutes} minutes...")

        # Отримуємо всі пристрої, які зараз позначені як активні
        active_devices = MinerDevice.objects.filter(is_active=True)
        
        now = timezone.now()
        cutoff_time = now - timedelta(minutes=timeout_minutes)
        
        devices_to_set_inactive = []

        for device in active_devices:
            # Знаходимо останній лог телеметрії для цього пристрою
            last_log = TelemetryLog.objects.filter(device=device).order_by('-timestamp').first()
            
            # Якщо логів немає, або останній лог був раніше, ніж наш поріг
            if not last_log or last_log.timestamp < cutoff_time:
                devices_to_set_inactive.append(device.id)
                self.stdout.write(self.style.WARNING(
                    f"Device {device.inventory_number} is inactive. Last seen: {last_log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if last_log else 'never'}. Setting to inactive."
                ))

        if devices_to_set_inactive:
            updated_count = MinerDevice.objects.filter(id__in=devices_to_set_inactive).update(is_active=False)
            self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} devices to inactive."))
        else:
            self.stdout.write(self.style.SUCCESS("No inactive devices found."))