from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from diploma.models import Employee, TelemetryLog

class Command(BaseCommand):
    help = 'Checks for inactive employees and sets their status to OFF_SHIFT'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=720,  # За замовчуванням 12 годин (720 хв) як резервне очищення
            help='Set the inactivity timeout in minutes.'
        )

    def handle(self, *args, **options):
        timeout_minutes = options['timeout']
        self.stdout.write(f"Starting check for employees inactive for more than {timeout_minutes} minutes...")

        # Отримуємо всіх працівників, які зараз НЕ "Не на зміні"
        active_employees = Employee.objects.exclude(safety_status='OFF_SHIFT').select_related('device')
        
        now = timezone.now()
        cutoff_time = now - timedelta(minutes=timeout_minutes)
        
        employees_to_set_offline = []

        for employee in active_employees:
            if not employee.device:
                continue

            # Знаходимо останній лог телеметрії для пристрою цього працівника
            last_log = TelemetryLog.objects.filter(device=employee.device).order_by('-timestamp').first()
            
            # Якщо логів немає, або останній лог був раніше, ніж наш поріг
            if not last_log or last_log.timestamp < cutoff_time:
                employees_to_set_offline.append(employee.id)
                # Створюємо "прощальний" системний запис телеметрії (примусове закриття)
                TelemetryLog.objects.create(
                    device=employee.device,
                    connected_repeater=last_log.connected_repeater if last_log else None,
                    wifi_signal_strength=0,
                    battery_level=0,
                    gas_level=last_log.gas_level if last_log else 0,
                    temperature=last_log.temperature if last_log else 0,
                    humidity=last_log.humidity if last_log else 0,
                    is_moving=False,
                    sos_reason="SYSTEM_AUTO_OFF_SHIFT"
                )
                
                self.stdout.write(self.style.WARNING(
                    f"Employee {employee} is inactive. Last seen: {last_log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if last_log else 'never'}. Setting to OFF_SHIFT."
                ))

        if employees_to_set_offline:
            updated_count = Employee.objects.filter(id__in=employees_to_set_offline).update(safety_status='OFF_SHIFT')
            self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} employees to OFF_SHIFT."))
        else:
            self.stdout.write(self.style.SUCCESS("No inactive employees found."))