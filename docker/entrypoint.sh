#!/bin/sh
set -e
python manage.py migrate --no-input
# One worker: the category cache is per-process and SQLite has one writer.
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 --workers 1 --threads 8 \
  --access-logfile - --error-logfile -
