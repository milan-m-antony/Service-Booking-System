import os
import django
import random
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_booking.settings')
django.setup()

from bookings.models import Service, ServiceCategory

def populate_services():
    data = {
        'Appliance Repair': [
            ('Washing Machine Repair', 450, 60),
            ('Refrigerator Repair', 550, 90),
            ('Microwave Repair', 350, 45)
        ],
        'Carpentry': [
            ('Door Lock Repair', 200, 30),
            ('Furniture Assembly', 800, 120)
        ],
        'Cleaning': [
            ('Kitchen Deep Cleaning', 1200, 180),
            ('Full Home Deep Cleaning', 3500, 300),
            ('Bathroom Cleaning', 400, 60)
        ],
        'Electrical': [
            ('MCB Replacement', 250, 30),
            ('Light Installation', 150, 20),
            ('Inverter Repair', 600, 60)
        ],
        'Home Cleaning': [
            ('Floor Scrubbing', 800, 120),
            ('Window Cleaning', 500, 90)
        ],
        'Painting': [
            ('Exterior Painting', 5000, 600),
            ('Texture Painting', 2500, 240)
        ],
        'Pest Control': [
            ('Cockroach Control', 700, 60),
            ('Termite Treatment', 2500, 180),
            ('General Pest Control', 1200, 120)
        ],
        'Plumbing': [
            ('Water Heater Repair', 400, 45),
            ('Taps & Leakage Fix', 150, 30),
            ('Drainage Unblocking', 600, 90)
        ],
        'Repair': [
            ('TV Repair', 800, 90),
            ('Laptop Repair', 1200, 120)
        ],
        'Salon': [
            ('Facial & Skin Care', 1500, 90),
            ('Hair Coloring', 2000, 120),
            ('Manicure & Pedicure', 1200, 60)
        ]
    }

    for cat_name, services in data.items():
        category, created = ServiceCategory.objects.get_or_create(name=cat_name)
        for name, price, duration in services:
            if not Service.objects.filter(name=name).exists():
                Service.objects.create(
                    name=name,
                    category=category,
                    price=Decimal(price),
                    duration_minutes=duration,
                    description=f"Professional {name} services by experts.",
                    is_active=True
                )
                print(f"Created service: {name} in {cat_name}")
            else:
                print(f"Service already exists: {name}")

if __name__ == "__main__":
    populate_services()
