import os
import datetime
import shutil
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from diploma.models import SystemSettings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

class Command(BaseCommand):
    help = 'Перевіряє стан бекапів, архівів та вільного місця на диску'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-email',
            action='store_true',
            help='Примусово додає тестову помилку для перевірки відправки Email',
        )

    def handle(self, *args, **options):
        now = timezone.localtime()
        issues = []

        # 1. Перевірка архівації (завдяки нашій новій моделі SystemSettings)
        sys_settings = SystemSettings.load()
        if sys_settings.last_archive_run:
            days_since_archive = (now.date() - sys_settings.last_archive_run).days
            if days_since_archive > 1:
                issues.append(f"⚠️ Архівація не виконувалась {days_since_archive} днів! (Остання: {sys_settings.last_archive_run})")
        else:
            issues.append("⚠️ Архівація ще жодного разу не виконувалась успішно (відсутній запис).")

        # 2. Перевірка бекапів (читаємо лог bash-скрипта)
        backup_log = os.path.join(settings.BASE_DIR, 'logs', 'cron_backup.log')
        if os.path.exists(backup_log):
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(backup_log), tz=datetime.timezone.utc)
            hours_since_backup = (timezone.now() - mtime).total_seconds() / 3600
            if hours_since_backup > 28: # 24 години + 4 години запасу
                issues.append(f"⚠️ Можливий збій бекапу БД. Останній запис у лог був {round(hours_since_backup, 1)} годин тому.")
        else:
            issues.append("⚠️ Файл логів бекапу не знайдено (logs/cron_backup.log).")

        # 3. Перевірка місця на диску
        total, used, free = shutil.disk_usage("/")
        free_gb = free // (2**30)
        if free_gb < 2:
            issues.append(f"⚠️ Критично мало місця на диску: залишилось лише {free_gb} GB!")
            
        # Якщо запущено з прапорцем --test-email, додаємо штучну проблему
        if options['test_email']:
            issues.append("🛠 ТЕСТ: Це перевірочне повідомлення для тестування системи відправки Email адміністратору.")

        # --- ВИВЕДЕННЯ РЕЗУЛЬТАТІВ ---
        self.stdout.write(self.style.SUCCESS(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Початок Health Check..."))
        
        if issues:
            self.stdout.write(self.style.ERROR("❌ ЗНАЙДЕНО ПРОБЛЕМИ:"))
            for issue in issues:
                self.stdout.write(self.style.WARNING(issue))
                
            # --- ВІДПРАВКА EMAIL АДМІНІСТРАТОРАМ ---
            superusers = User.objects.filter(is_superuser=True).exclude(email__exact='')
            emails = [user.email for user in superusers]
            
            if emails:
                subject = '⚠️ Глибина 4.0 - Проблеми із сервером (Health Check)'
                
                html_message = render_to_string('diploma/auth/health_check_email.html', {
                    'issues': issues,
                    'time': now
                })
                plain_message = strip_tags(html_message)
                
                try:
                    send_mail(subject, plain_message, settings.DEFAULT_FROM_EMAIL, emails, html_message=html_message, fail_silently=True)
                    self.stdout.write(self.style.SUCCESS(f"📧 Повідомлення відправлено адмінам: {', '.join(emails)}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Помилка відправки Email: {e}"))
            else:
                self.stdout.write(self.style.WARNING("⚠️ Email не відправлено: не знайдено адмінів з вказаною поштою."))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Система повністю здорова. Бекапи та архіви оновлюються, місця на диску достатньо."))