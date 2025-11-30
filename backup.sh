#!/bin/bash

# Налаштування
BACKUP_DIR="/var/backups/django_project"
PROJECT_DIR="/var/www/django_project"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL налаштування
DB_NAME="django_project"
DB_USER="bunb"
DB_HOST="localhost"
DB_PORT="5432"

# Створюємо директорію для бекапів
mkdir -p $BACKUP_DIR

# Бекап бази даних PostgreSQL
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -F c -f $BACKUP_DIR/db_backup_$DATE.dump

# Бекап медіа-файлів (якщо є)
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz $PROJECT_DIR/media/ 2>/dev/null || true

# Експорт даних Django у JSON
cd $PROJECT_DIR
source venv/bin/activate
python manage.py dumpdata --indent=2 > $BACKUP_DIR/data_export_$DATE.json

# Видаляємо старі бекапи (старіше 30 днів)
find $BACKUP_DIR -name "*.dump" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.json" -mtime +30 -delete

echo "Backup completed: $DATE"