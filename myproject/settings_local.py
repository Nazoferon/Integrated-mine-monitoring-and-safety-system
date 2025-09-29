from .settings import *
import os

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# База даних SQLite для локального тестування
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Вимкнути SSL для локального середовища
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Правильні налаштування статичних файлів для розробки
STATIC_URL = '/static/'

# Шлях до статичних файлів під час розробки
STATICFILES_DIRS = [
    BASE_DIR / "static",  # основна папка static
    BASE_DIR / "portfolio/static",  # статичні файли додатка portfolio
    BASE_DIR / "diploma/static",  # статичні файли додатка diploma
]

# Для збору статичних файлів (не обов'язково для розробки)
STATIC_ROOT = BASE_DIR / "staticfiles"

# Медіа файли (якщо є)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Додаткові налаштування для розробки
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# local testing - python manage.py runserver --settings=myproject.settings_local