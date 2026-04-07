import os
import gzip
import csv
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from diploma.models import TelemetryLog

class Command(BaseCommand):
    help = 'Архівує стару телеметрію (старше 30 днів) у GZIP-архів і видаляє файли старіші за 6 місяців.'

    def handle(self, *args, **options):
        # Гарантуємо існування папок для архівів та логів одразу при запуску
        archive_dir = os.path.join(settings.BASE_DIR, 'archives', 'telemetry')
        os.makedirs(archive_dir, exist_ok=True)
        
        now = timezone.now()
        archive_cutoff = now - timedelta(days=30)
        delete_cutoff = now - timedelta(days=180) # 6 місяців
        
        # --- 1. АРХІВУВАННЯ ---
        old_logs = TelemetryLog.objects.filter(timestamp__lt=archive_cutoff, is_sos=False)
        count = old_logs.count()
        
        if count > 0:
            self.stdout.write(f"Знайдено {count} записів для архівації. Починаємо...")
            
            # Формуємо унікальне ім'я файлу на основі часу
            filename = f"telemetry_archive_{now.strftime('%Y%m%d_%H%M%S')}.csv.gz"
            filepath = os.path.join(archive_dir, filename)
            
            # Відкриваємо gzip файл для запису тексту (wt - write text)
            with gzip.open(filepath, 'wt', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                # Пишемо заголовки
                writer.writerow(['id', 'device_mac', 'timestamp', 'repeater_uid', 'rssi', 'temp', 'humidity', 'gas_lel', 'battery'])
                
                # Використовуємо .iterator(chunk_size) щоб не забити оперативну пам'ять (RAM)
                for log in old_logs.iterator(chunk_size=5000):
                    writer.writerow([
                        log.id,
                        log.device.mac_address,
                        log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        log.connected_repeater.uid if log.connected_repeater else 'OFFLINE',
                        log.wifi_signal_strength,
                        log.temperature,
                        log.humidity,
                        log.gas_level,
                        log.battery_level
                    ])
            
            self.stdout.write(self.style.SUCCESS(f"Дані стиснено і збережено в: {filepath}"))
            
            # Видаляємо дані з БД ТІЛЬКИ якщо файл успішно створився (транзакційність архівації)
            deleted_count, _ = old_logs.delete()
            self.stdout.write(self.style.SUCCESS(f"Видалено з БД {deleted_count} рядків."))
        else:
            self.stdout.write("Немає записів для архівації (старіших за 30 днів).")
            
        # --- 2. ВИДАЛЕННЯ СТАРИХ АРХІВІВ (старше 6 місяців) ---
        self.stdout.write("Перевірка старих архівів на диску...")
        archive_dir = os.path.join(settings.BASE_DIR, 'archives', 'telemetry')
        if os.path.exists(archive_dir):
            for file in os.listdir(archive_dir):
                file_path = os.path.join(archive_dir, file)
                if os.path.isfile(file_path) and file.endswith('.csv.gz'):
                    # Отримуємо час модифікації файлу і перевіряємо чи він старіший за 180 днів
                    file_mtime = timezone.datetime.fromtimestamp(os.path.getmtime(file_path), tz=timezone.utc)
                    if file_mtime < delete_cutoff:
                        os.remove(file_path)
                        self.stdout.write(self.style.WARNING(f"Видалено застарілий архів: {file}"))
                        
        self.stdout.write(self.style.SUCCESS("Процес обслуговування БД успішно завершено."))