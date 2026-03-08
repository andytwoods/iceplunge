#!/bin/bash
set -e

echo "=== Waiting for database ==="
python manage.py wait_for_db 2>/dev/null || python -c "
import os, time, psycopg
url = os.environ['DATABASE_URL']
for i in range(30):
    try:
        psycopg.connect(url).close()
        print('Database ready.')
        break
    except Exception as e:
        print(f'Waiting for DB... ({e})')
        time.sleep(2)
"

echo "=== Running migrations ==="
python manage.py migrate --verbosity 2

echo "=== Running setup ==="
python manage.py setup_app
