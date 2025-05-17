#!/bin/sh

# Wait until PostgreSQL is ready
echo "Waiting for PostgreSQL..."

while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 1
done

echo "PostgreSQL started"

# Apply migrations
python manage.py migrate

# Run seeder
python manage.py seed_configuration

# Run celery worker
python manage.py setup_celery_beat

exec "$@"
