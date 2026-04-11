#!/bin/bash

# Шляхи
BACKUP_DIR="/var/backups/django_project"
PROJECT_DIR="/var/www/django_project"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Переходимо в директорію проєкту і активуємо віртуальне середовище
cd "$PROJECT_DIR" || exit
source "$PROJECT_DIR/venv/bin/activate"

# 1. Дамп бази даних PostgreSQL (нативно)
# Автоматично дістаємо пароль з файлу .env, щоб не вводити його вручну
export PGPASSWORD=$(python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); print(os.getenv('DB_PASSWORD', ''))")
pg_dump -U bunb -h localhost -w -F c django_project > "$BACKUP_DIR/db_backup_$TIMESTAMP.dump"

# 2. Експорт даних Django у JSON
python manage.py dumpdata > "$BACKUP_DIR/data_export_$TIMESTAMP.json"

# 3. Бекап медіа-файлів (фотографії працівників тощо)
tar -czf "$BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz" -C "$PROJECT_DIR" media/

# 4. Видалення старих бекапів (старших за 7 днів)
find "$BACKUP_DIR" -type f -name "*.dump" -mtime +7 -delete
find "$BACKUP_DIR" -type f -name "*.json" -mtime +7 -delete
find "$BACKUP_DIR" -type f -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $TIMESTAMP"

