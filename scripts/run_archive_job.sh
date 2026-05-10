#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/var/www/django_project"
LOG_DIR="$PROJECT_DIR/logs"
LOCK_FILE="/tmp/django_project_archive.lock"
LOG_FILE="$LOG_DIR/cron_archive_telemetry.log"

mkdir -p "$LOG_DIR"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] archive job started"
  flock -n 9 || {
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] archive job skipped (lock is held)"
    exit 0
  }

  cd "$PROJECT_DIR"
  "$PROJECT_DIR/venv/bin/python" manage.py archive_telemetry --days 30 --keep-files 180
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] archive job finished successfully"
} 9>"$LOCK_FILE" >> "$LOG_FILE" 2>&1
