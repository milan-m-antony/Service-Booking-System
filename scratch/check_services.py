import os
import django
from django.db.models import Avg, Count

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_booking.settings')
django.setup()

from bookings.models import Service, ServiceCategory

services = Service.objects.all()
print(f"Total Services: {services.count()}")
for s in services:
    print(f"- {s.name} ({s.category.name}): Price={s.price}, Duration={s.duration_minutes}min, Image={s.image}")

categories = ServiceCategory.objects.all()
print(f"\nTotal Categories: {categories.count()}")
for c in categories:
    print(f"- {c.name}")
