from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from diploma.models import TelemetryLog

class Command(BaseCommand):
    help = 'Видаляє стару телеметрію (старше 30 днів), залишаючи лише записи про інциденти.'

    def handle(self, *args, **options):
        cutoff_date = timezone.now() - timedelta(days=30)
        
        # Шукаємо записи старіші за 30 днів, які НЕ є тривогами (is_sos=False)
        old_logs = TelemetryLog.objects.filter(timestamp__lt=cutoff_date, is_sos=False)
        count, _ = old_logs.delete()
        
        if count > 0:
            self.stdout.write(self.style.SUCCESS(f"Успішно видалено {count} старих записів телеметрії."))
        else:
            self.stdout.write("Немає старих записів для видалення.")