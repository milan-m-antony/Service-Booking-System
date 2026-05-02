from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from bookings.models import CustomUser

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds the database with default users for testing."

    def handle(self, *args, **kwargs):
        # Create Admin
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                password="admin",
                email="admin@example.com",
                role=CustomUser.Roles.ADMIN
            )
            self.stdout.write(self.style.SUCCESS("Successfully created admin/admin"))
        else:
            self.stdout.write("Admin user already exists.")

        # Create Staff
        if not User.objects.filter(username="staff").exists():
            User.objects.create_user(
                username="staff",
                password="staff",
                email="staff@example.com",
                role=CustomUser.Roles.STAFF
            )
            self.stdout.write(self.style.SUCCESS("Successfully created staff/staff"))
        else:
            self.stdout.write("Staff user already exists.")

        # Create Customer
        if not User.objects.filter(username="user").exists():
            User.objects.create_user(
                username="user",
                password="user",
                email="user@example.com",
                role=CustomUser.Roles.CUSTOMER
            )
            self.stdout.write(self.style.SUCCESS("Successfully created user/user"))
        else:
            self.stdout.write("Customer user already exists.")

        self.stdout.write(self.style.SUCCESS("Seeding complete!"))
