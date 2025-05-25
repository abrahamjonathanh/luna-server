from django.core.management.base import BaseCommand
from api.models import Role

class Command(BaseCommand):
    help = "Seed default Role data"

    def handle(self, *args, **options):
        data = ["Admin", "Guest"]

        # Store it in db
        for role in data:
            try:
                Role.objects.create(role=role)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Role {role} already exists."))
                continue

        self.stdout.write(self.style.SUCCESS("Default Role data seeded successfully."))
        