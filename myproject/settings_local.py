from .settings import *
import os
from pathlib import Path

# 1. Вмикаємо режим дебагу для розробки
DEBUG = True

# 2. Дозволяємо локальні хости
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']

# 3. Перевизначаємо базу даних на SQLite, щоб не піднімати PostgreSQL локально
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 4. Відключаємо продакшен-безпеку (HTTPS, захищені кукі)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_PROXY_SSL_HEADER = None

# 5. Налаштування статики
# В основному файлі STATIC_ROOT вказує на серверний шлях (/var/www/...). 
# Перевизначаємо його на локальну папку.
STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "portfolio/static",
    BASE_DIR / "diploma/static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# 6. Налаштування Email
# Під час розробки зручніше бачити листи просто в консолі, щоб не спамити реальну пошту.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# (Якщо тобі прямо зараз потрібно тестувати реальну відправку листів локально, 
# просто закоментуй рядок вище. Django автоматично візьме SMTP-налаштування 
# з твого основного файлу settings.py)

# 7. Додаткові налаштування для розробки
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]


# local testing - python manage.py runserver --settings=myproject.settings_local