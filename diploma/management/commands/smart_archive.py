from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from diploma.models import SystemSettings

class Command(BaseCommand):
    help = 'Розумний планувальник для перевірки та запуску архівації на основі налаштувань з БД'

    def handle(self, *args, **options):
        settings = SystemSettings.load()
        now = timezone.localtime()  # Враховує TIME_ZONE='Europe/Kyiv'
        current_time = now.time()
        today = now.date()

        # Перевіряємо: чи настав час архівації?
        if current_time >= settings.archive_time:
            # Перевіряємо: чи ми ВЖЕ робили архівацію сьогодні?
            if settings.last_archive_run != today:
                self.stdout.write(self.style.WARNING(f"[{now}] Час настав. Запускаємо архівацію..."))
                try:
                    # Викликаємо ВАШУ існуючу команду з динамічними аргументами!
                    call_command(
                        'archive_telemetry', 
                        days=settings.archive_older_than_days, 
                        keep_files=settings.keep_archives_count
                    )
                    
                    # Оновлюємо статус успішного запуску
                    settings.last_archive_run = today
                    settings.save()
                    self.stdout.write(self.style.SUCCESS("Архівацію успішно завершено та зафіксовано в БД."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Помилка архівації: {e}"))
            else:
                self.stdout.write(f"[{now}] Архівація за сьогодні вже була успішно виконана.")
        else:
            self.stdout.write(f"[{now}] Ще не час. Архівація запланована на {settings.archive_time}.")