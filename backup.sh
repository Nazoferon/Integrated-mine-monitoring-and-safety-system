#!/bin/bash

# Шляхи
BACKUP_DIR="/var/backups/django_project"
PROJECT_DIR="/var/www/django_project"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Переходимо в директорію проєкту і активуємо віртуальне середовище
cd "$PROJECT_DIR" || exit
source "$PROJECT_DIR/venv/bin/activate"
mkdir -p "$BACKUP_DIR"

# Підтягуємо конфіг БД з .env, щоб не дублювати параметри у скрипті
DB_NAME=$(python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); print(os.getenv('DB_NAME', 'django_project'))")
DB_USER=$(python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); print(os.getenv('DB_USER', 'bunb'))")
DB_HOST=$(python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); print(os.getenv('DB_HOST', 'localhost'))")
DB_PASSWORD=$(python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); print(os.getenv('DB_PASSWORD', ''))")

# 1. Дамп бази даних PostgreSQL (нативно)
# Автоматично дістаємо пароль з файлу .env, щоб не вводити його вручну
export PGPASSWORD="$DB_PASSWORD"
pg_dump -U "$DB_USER" -h "$DB_HOST" -w -F c "$DB_NAME" > "$BACKUP_DIR/db_backup_$TIMESTAMP.dump"

# 2. Експорт даних Django у JSON
python manage.py dumpdata > "$BACKUP_DIR/data_export_$TIMESTAMP.json"

# 3. Бекап медіа-файлів (фотографії працівників тощо)
tar -czf "$BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz" -C "$PROJECT_DIR" media/

# 4. Видалення старих бекапів (старших за 7 днів)
find "$BACKUP_DIR" -type f -name "*.dump" -mtime +7 -delete
find "$BACKUP_DIR" -type f -name "*.json" -mtime +7 -delete
find "$BACKUP_DIR" -type f -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $TIMESTAMP"

