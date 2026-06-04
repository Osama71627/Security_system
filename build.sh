#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

if [ -z "$DATABASE_URL" ]; then
    echo "=========================================="
    echo "  WARNING: DATABASE_URL is not set!"
    echo "  Create a PostgreSQL database in Render"
    echo "  and add DATABASE_URL to Environment"
    echo "  Otherwise SQLite will be used (DATA WILL BE LOST ON RESTART)"
    echo "=========================================="
fi

python manage.py collectstatic --no-input
python manage.py migrate
