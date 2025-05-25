from django.core.management.base import BaseCommand
from api.models import Configuration

class Command(BaseCommand):
    help = "Seed default Configuration data"

    def handle(self, *args, **options):
        data = [
            ("ALERT_ACTIVATED", "False"),
            ("RECIPIENTS", "[]"),
            ("SEND_EMAIL_EVERY", "10"),
            ("DEFAULT_DATE_RANGE", "7D"),
            ("ERROR_RATE_THRESHOLD", "5"),
            ("ERROR_THRESHOLD", "25"),
            ("RESPONSE_TIME_THRESHOLD", "10000"),
        ]

        # Store it in db
        for key, value in data:
            try:
                Configuration.objects.create(key=key, value=value)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Configuration {key} already exists."))
                continue

        self.stdout.write(self.style.SUCCESS("Default Configuration data seeded successfully."))
        