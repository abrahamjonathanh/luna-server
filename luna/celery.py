import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'luna.settings')

app = Celery('luna')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()  # Auto-discover tasks in all apps