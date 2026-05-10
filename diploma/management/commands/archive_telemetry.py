import os
import csv
import gzip
import urllib.request
import datetime
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.db.models import Max, Avg, Count
from diploma.models import TelemetryLog, SecurityAlert

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_INSTALLED = True
except ImportError:
    REPORTLAB_INSTALLED = False

class Command(BaseCommand):
    help = 'Архівує телеметрію, старшу за X днів, у CSV.gz та генерує PDF-звіт'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Кількість днів для зберігання в БД (решта архівується)')
        parser.add_argument('--keep-files', type=int, default=180, help='Скільки днів зберігати згенеровані CSV.gz та PDF файли на диску')

    def handle(self, *args, **options):
        days = options['days']
        keep_files_days = options['keep_files']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        logs_to_archive = TelemetryLog.objects.filter(timestamp__lt=cutoff_date)
        count = logs_to_archive.count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING(f"Немає даних для архівації (старших за {days} днів)."))
            return

        # 1. Створюємо директорії для архівів
        archive_dir = os.path.join(settings.BASE_DIR, 'archives', 'telemetry')
        reports_dir = os.path.join(settings.BASE_DIR, 'archives', 'reports')
        os.makedirs(archive_dir, exist_ok=True)
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp_str = timezone.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"telemetry_archive_{timestamp_str}.csv.gz"
        csv_filepath = os.path.join(archive_dir, csv_filename)
        pdf_filename = f"report_{timestamp_str}.pdf"
        pdf_filepath = os.path.join(reports_dir, pdf_filename)
        
        self.stdout.write(f"Знайдено {count} записів. Починаємо архівацію...")

        # 2. Збираємо статистику для PDF-звіту ДО видалення даних
        stats = logs_to_archive.aggregate(
            max_gas=Max('gas_level'),
            avg_temp=Avg('temperature'),
            avg_hum=Avg('humidity')
        )
        
        # АГРЕГАЦІЯ 1: Знаходимо Топ-3 пристрої з найвищими показниками газу
        top_gas_devices = logs_to_archive.values('device__inventory_number') \
            .annotate(max_gas=Max('gas_level')) \
            .filter(max_gas__gt=0) \
            .order_by('-max_gas')[:3]

        # АГРЕГАЦІЯ 2: Аналіз причин тривог
        alerts_to_archive = SecurityAlert.objects.filter(created_at__lt=cutoff_date)
        alerts_count = alerts_to_archive.count()
        alerts_breakdown = alerts_to_archive.values('reason') \
            .annotate(count=Count('id')) \
            .order_by('-count')[:5]

        # 3. Експорт у стиснутий CSV.gz (оптимізація пам'яті через chunks)
        with gzip.open(csv_filepath, 'wt', encoding='utf-8', newline='') as gz_file:
            writer = csv.writer(gz_file)
            writer.writerow(['ID', 'Timestamp', 'Device_MAC', 'Repeater_UID', 'Battery', 'Gas_LEL', 'Temp', 'Humidity', 'Is_SOS', 'Is_Moving'])
            
            for log in logs_to_archive.select_related('device', 'connected_repeater').iterator(chunk_size=5000):
                writer.writerow([
                    log.id,
                    log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    log.device.mac_address,
                    log.connected_repeater.uid if log.connected_repeater else 'N/A',
                    log.battery_level,
                    log.gas_level,
                    log.temperature,
                    log.humidity,
                    log.is_sos,
                    log.is_moving
                ])

        # 4. Генерація офіційного PDF-звіту
        if REPORTLAB_INSTALLED:
            self.generate_pdf(pdf_filepath, stats, count, alerts_count, alerts_breakdown, top_gas_devices, cutoff_date)
        else:
            self.stdout.write(self.style.ERROR("Бібліотека reportlab не встановлена. PDF не згенеровано."))

        # 5. Безпечне видалення з Бази Даних
        with transaction.atomic():
            logs_to_archive._raw_delete(logs_to_archive.db)
            
        self.stdout.write(self.style.SUCCESS(f"✅ Успішно архівовано {count} записів у {csv_filename}"))
        if REPORTLAB_INSTALLED:
            self.stdout.write(self.style.SUCCESS(f"✅ PDF-звіт збережено у {pdf_filename}"))

        # 6. Очищення застарілих фізичних файлів з диска (CSV та PDF)
        self.cleanup_old_files(archive_dir, keep_files_days)
        self.cleanup_old_files(reports_dir, keep_files_days)

    def generate_pdf(self, filepath, stats, logs_count, alerts_count, alerts_breakdown, top_gas_devices, cutoff_date):
        # Завантажуємо кириличний шрифт (DejaVu), бо стандартні PDF-шрифти не розуміють українську
        font_path = os.path.join(settings.BASE_DIR, "DejaVuSans.ttf")
        if not os.path.exists(font_path):
            self.stdout.write("Завантаження шрифту для підтримки кирилиці...")
            urllib.request.urlretrieve("https://raw.githubusercontent.com/prawnpdf/prawn/master/data/fonts/DejaVuSans.ttf", font_path)
            
        pdfmetrics.registerFont(TTFont('DejaVu', font_path))
        
        c = canvas.Canvas(filepath, pagesize=A4)
        width, height = A4
        
        # Шапка звіту
        c.setFont("DejaVu", 18)
        c.drawString(50, height - 60, "Офіційний Звіт: Система Безпеки «Глибина 4.0»")
        
        c.setFont("DejaVu", 12)
        c.drawString(50, height - 100, f"Дата генерації звіту: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
        c.drawString(50, height - 120, f"Період архівування: дані до {cutoff_date.strftime('%Y-%m-%d')}")
        
        c.line(50, height - 140, width - 50, height - 140)
        
        # Блок статистики
        c.setFont("DejaVu", 14)
        c.drawString(50, height - 170, "1. Аналітика телеметрії (Архів):")
        
        c.setFont("DejaVu", 12)
        c.drawString(70, height - 200, f"• Загальна кількість збережених пакетів даних: {logs_count}")
        c.drawString(70, height - 220, f"• Максимальний зафіксований рівень метану (CH4): {stats['max_gas'] or 0}% LEL")
        c.drawString(70, height - 240, f"• Середня температура у штреках: {round(stats['avg_temp'] or 0, 1)} °C")
        c.drawString(70, height - 260, f"• Середня вологість повітря: {round(stats['avg_hum'] or 0, 1)} %")
        
        y_pos = height - 290
        c.drawString(50, y_pos, "Топ-3 пристрої з найбільшими викидами метану (CH4):")
        y_pos -= 25
        if top_gas_devices:
            for dev in top_gas_devices:
                c.drawString(70, y_pos, f"• Датчик [{dev['device__inventory_number']}]: {dev['max_gas']}% LEL")
                y_pos -= 20
        else:
            c.drawString(70, y_pos, "• Викидів метану не зафіксовано.")
            y_pos -= 20

        # Блок інцидентів
        y_pos -= 20
        c.setFont("DejaVu", 14)
        c.drawString(50, y_pos, "2. Інциденти та безпека:")
        y_pos -= 30
        c.setFont("DejaVu", 12)
        c.drawString(70, y_pos, f"• Всього зафіксовано інцидентів (тривог): {alerts_count}")
        y_pos -= 25
        if alerts_breakdown:
            c.drawString(70, y_pos, "Розподіл за причинами:")
            y_pos -= 20
            for alert in alerts_breakdown:
                c.drawString(90, y_pos, f"- {alert['reason'][:60]}: {alert['count']} випадків")
                y_pos -= 20
        
        # Офіційна примітка про наявність CSV
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.setFont("DejaVu", 10)
        c.drawString(50, 80, "* Примітка: Цей документ є стислим аналітичним зведенням (Executive Summary).")
        c.drawString(50, 65, f"Повний масив сирих даних ({logs_count} записів) надійно збережено в супровідному")
        c.drawString(50, 50, "архіві формату .csv.gz для подальшого машинного аналізу.")
        c.setFillColorRGB(0, 0, 0)
        c.drawString(50, 30, "Згенеровано автоматичною системою (Data Lifecycle Management) Глибина 4.0.")
        c.save()

    def cleanup_old_files(self, directory, max_days):
        cutoff_time = timezone.now() - timedelta(days=max_days)
        if os.path.exists(directory):
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path), tz=datetime.timezone.utc)
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        self.stdout.write(self.style.WARNING(f"🗑️ Видалено застарілий файл: {file}"))