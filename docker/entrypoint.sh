#!/usr/bin/env bash
set -e

echo "[entrypoint] Waiting for PostgreSQL ${DB_HOST}:${DB_PORT} ..."
until nc -z "${DB_HOST}" "${DB_PORT}"; do
  sleep 1
done

echo "[entrypoint] PostgreSQL is ready"

echo "[entrypoint] Running migrations ..."
python manage.py migrate --noinput

echo "[entrypoint] Collecting static ..."
python manage.py collectstatic --noinput

echo "[entrypoint] Starting Gunicorn ..."
exec gunicorn myproject.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --access-logfile - \
  --error-logfile -