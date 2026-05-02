from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from bookings.models import CustomUser

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds the database with default users for testing."

    def handle(self, *args, **kwargs):
        # Create Admin
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "role": CustomUser.Roles.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            }
        )
        if created:
            admin_user.set_password("admin")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created admin/admin"))

        # Create Staff
        staff_user, created = User.objects.get_or_create(
            username="staff",
            defaults={
                "email": "staff@example.com",
                "role": CustomUser.Roles.STAFF,
                "is_staff": True,
            }
        )
        if created:
            staff_user.set_password("staff")
            staff_user.save()
            self.stdout.write(self.style.SUCCESS("Created staff/staff"))

        # Create Customer
        user_user, created = User.objects.get_or_create(
            username="user",
            defaults={
                "email": "user@example.com",
                "role": CustomUser.Roles.CUSTOMER,
            }
        )
        if created:
            user_user.set_password("user")
            user_user.save()
            self.stdout.write(self.style.SUCCESS("Created user/user"))

        # --- SEED CATEGORIES ---
        from bookings.models import ServiceCategory, Service
        
        categories_data = [
            {"name": "Cleaning", "icon": "✨", "color": "#10b981"},
            {"name": "Plumbing", "icon": "🚰", "color": "#3b82f6"},
            {"name": "Electrical", "icon": "⚡", "color": "#f59e0b"},
        ]
        
        categories = {}
        for cat_data in categories_data:
            cat, created = ServiceCategory.objects.get_or_create(
                name=cat_data["name"],
                defaults={"icon": cat_data["icon"], "color": cat_data["color"]}
            )
            categories[cat.name] = cat
            if created:
                self.stdout.write(f"Created category: {cat.name}")

        # --- SEED SERVICES ---
        services_data = [
            {"name": "Basic House Cleaning", "cat": "Cleaning", "price": 50, "dur": 120},
            {"name": "Deep Kitchen Cleaning", "cat": "Cleaning", "price": 80, "dur": 180},
            {"name": "Leaky Tap Repair", "cat": "Plumbing", "price": 40, "dur": 60},
            {"name": "Full Pipe Inspection", "cat": "Plumbing", "price": 120, "dur": 120},
            {"name": "AC Maintenance", "cat": "Electrical", "price": 100, "dur": 90},
            {"name": "Switchboard Repair", "cat": "Electrical", "price": 30, "dur": 45},
        ]

        for s_data in services_data:
            service, created = Service.objects.get_or_create(
                name=s_data["name"],
                defaults={
                    "category": categories[s_data["cat"]],
                    "price": s_data["price"],
                    "duration_minutes": s_data["dur"],
                    "description": f"Professional {s_data['name']} service.",
                }
            )
            if created:
                # Assign the staff user to this service
                service.staff.add(staff_user)
                self.stdout.write(f"Created service: {service.name} (Assigned to staff)")

        self.stdout.write(self.style.SUCCESS("Seeding complete!"))

