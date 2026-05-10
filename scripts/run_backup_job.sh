#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/var/www/django_project"
LOG_DIR="$PROJECT_DIR/logs"
LOCK_FILE="/tmp/django_project_backup.lock"
LOG_FILE="$LOG_DIR/cron_backup.log"

mkdir -p "$LOG_DIR"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] backup job started"
  flock -n 9 || {
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] backup job skipped (lock is held)"
    exit 0
  }

  "$PROJECT_DIR/backup.sh"
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] backup job finished successfully"
} 9>"$LOCK_FILE" >> "$LOG_FILE" 2>&1
