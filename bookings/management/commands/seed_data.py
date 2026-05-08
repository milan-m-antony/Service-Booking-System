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
        
        categories_config = [
            {"name": "Cleaning", "icon": "brush", "color": "#10b981"},
            {"name": "Electrical", "icon": "bolt", "color": "#f59e0b"},
            {"name": "Plumbing", "icon": "shower", "color": "#3b82f6"},
            {"name": "Grooming", "icon": "cut", "color": "#ec4899"},
            {"name": "Appliance Repair", "icon": "ac_unit", "color": "#06b6d4"},
            {"name": "Handyman", "icon": "build", "color": "#71717a"},
            {"name": "Painting", "icon": "format_paint", "color": "#8b5cf6"},
        ]
        
        categories = {}
        for cat_data in categories_config:
            cat, created = ServiceCategory.objects.get_or_create(
                name=cat_data["name"],
                defaults={"icon": cat_data["icon"], "color": cat_data["color"]}
            )
            categories[cat.name] = cat
            if created:
                self.stdout.write(f"Created category: {cat.name}")

        # --- SEED SERVICES ---
        services_config = [
            # Cleaning
            {"name": "1BHK Deep Cleaning", "cat": "Cleaning", "price": 2500, "dur": 180},
            {"name": "2BHK Deep Cleaning", "cat": "Cleaning", "price": 4000, "dur": 240},
            {"name": "Bathroom Cleaning", "cat": "Cleaning", "price": 600, "dur": 60},
            {"name": "Kitchen Cleaning", "cat": "Cleaning", "price": 1200, "dur": 120},
            {"name": "Sofa Cleaning (per seat)", "cat": "Cleaning", "price": 250, "dur": 45},
            {"name": "Carpet Cleaning", "cat": "Cleaning", "price": 500, "dur": 90},
            
            # Electrical
            {"name": "Switch/Socket Repair", "cat": "Electrical", "price": 150, "dur": 30},
            {"name": "Fan Installation", "cat": "Electrical", "price": 300, "dur": 45},
            {"name": "Light Installation", "cat": "Electrical", "price": 200, "dur": 30},
            {"name": "Inverter Installation", "cat": "Electrical", "price": 1000, "dur": 120},
            {"name": "Full House Wiring", "cat": "Electrical", "price": 15000, "dur": 480},
            
            # Plumbing
            {"name": "Tap Repair", "cat": "Plumbing", "price": 150, "dur": 30},
            {"name": "Pipe Leakage Fix", "cat": "Plumbing", "price": 400, "dur": 60},
            {"name": "Toilet Installation", "cat": "Plumbing", "price": 1000, "dur": 120},
            {"name": "Drain Cleaning", "cat": "Plumbing", "price": 300, "dur": 60},
            {"name": "Water Tank Cleaning", "cat": "Plumbing", "price": 1500, "dur": 120},
            
            # Grooming
            {"name": "Men's Haircut", "cat": "Grooming", "price": 250, "dur": 45},
            {"name": "Beard Trim", "cat": "Grooming", "price": 150, "dur": 30},
            {"name": "Women's Haircut", "cat": "Grooming", "price": 1000, "dur": 60},
            {"name": "Facial", "cat": "Grooming", "price": 1500, "dur": 90},
            {"name": "Bridal Makeup", "cat": "Grooming", "price": 10000, "dur": 180},
            
            # Appliance Repair
            {"name": "AC Service", "cat": "Appliance Repair", "price": 600, "dur": 60},
            {"name": "AC Installation", "cat": "Appliance Repair", "price": 1800, "dur": 120},
            {"name": "Washing Machine Repair", "cat": "Appliance Repair", "price": 800, "dur": 90},
            {"name": "Refrigerator Repair", "cat": "Appliance Repair", "price": 700, "dur": 90},
            {"name": "TV Repair", "cat": "Appliance Repair", "price": 1200, "dur": 90},
            
            # Handyman
            {"name": "Furniture Assembly", "cat": "Handyman", "price": 600, "dur": 90},
            {"name": "TV Wall Mount", "cat": "Handyman", "price": 500, "dur": 45},
            {"name": "Curtain Rod Installation", "cat": "Handyman", "price": 300, "dur": 30},
            {"name": "Door Repair", "cat": "Handyman", "price": 700, "dur": 60},
            
            # Painting
            {"name": "Painting (Per Sq Ft)", "cat": "Painting", "price": 20, "dur": 10},
            {"name": "1 Room Painting", "cat": "Painting", "price": 6000, "dur": 480},
            {"name": "Full House Painting", "cat": "Painting", "price": 50000, "dur": 1440},
        ]

        for s_data in services_config:
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
                self.stdout.write(f"Created service: {service.name}")

        self.stdout.write(self.style.SUCCESS("Seeding complete!"))


