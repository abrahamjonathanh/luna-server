from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule

class Command(BaseCommand):
    help = "Creates a periodic task for Celery Beat"

    def handle(self, *args, **options):
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=10,
            period=IntervalSchedule.MINUTES,
        )

        task, created = PeriodicTask.objects.get_or_create(
            name="Check API Errors Interval",
            task="api.tasks.check_error_rates_and_alert",
            interval=schedule,
            defaults={'enabled': True},
        )

        if created:
            self.stdout.write(self.style.SUCCESS("Periodic task created!"))
        else:
            self.stdout.write(self.style.WARNING("Task already exists."))