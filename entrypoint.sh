#!/bin/sh

# Wait until PostgreSQL is ready
echo "Waiting for PostgreSQL..."

while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 1
done

echo "PostgreSQL started"

# Apply migrations
python manage.py migrate
python manage.py collectstatic --noinput

# Run seeder
python manage.py seed_configuration

python manage.py seed_role

# Run celery worker
python manage.py setup_celery_beat

exec "$@"
