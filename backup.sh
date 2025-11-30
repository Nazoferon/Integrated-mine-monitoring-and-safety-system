#!/bin/bash

# Налаштування
BACKUP_DIR="/var/backups/django_project"
PROJECT_DIR="/var/www/django_project"
DB_NAME="$PROJECT_DIR/db.sqlite3"
DATE=$(date +%Y%m%d_%H%M%S)

# Створюємо директорію для бекапів
mkdir -p $BACKUP_DIR

# Бекап бази даних
cp $DB_NAME $BACKUP_DIR/db_backup_$DATE.sqlite3

# Бекап медіа-файлів (якщо є)
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz $PROJECT_DIR/media/ 2>/dev/null || true

# Експорт даних Django у JSON
cd $PROJECT_DIR
source venv/bin/activate
python manage.py dumpdata --indent=2 > $BACKUP_DIR/data_export_$DATE.json

# Видаляємо старі бекапи (старіше 30 днів)
find $BACKUP_DIR -name "*.sqlite3" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.json" -mtime +30 -delete

echo "Backup completed: $DATE"