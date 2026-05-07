import os
import shutil
from django.conf import settings
from django.core.files import File
from bookings.models import Service

def slugify(text):
    return text.lower().replace(' ', '-').replace('&', 'and').replace('/', '-')

def migrate_images():
    # Source directory for generic images
    static_img_dir = os.path.join(settings.BASE_DIR, 'bookings', 'static', 'bookings', 'images', 'categories')
    
    # Target directory in media
    media_services_dir = os.path.join(settings.MEDIA_ROOT, 'services')
    if not os.path.exists(media_services_dir):
        os.makedirs(media_services_dir)
        print(f"Created {media_services_dir}")

    # Mapping keywords/categories to static files
    mapping = {
        'shelf': 'shelf.jpg',
        'lock': 'lock.jpg',
        'furniture': 'furniture.jpg',
        'cleaning': 'cleaning.jpg',
        'plumbing': 'plumbing.jpg',
        'taps': 'plumbing.jpg',
        'painting': 'painting.jpg',
        'pest': 'pest_control.jpg',
        'cockroach': 'pest_control.jpg',
        'termite': 'pest_control.jpg',
        'hair': 'grooming.jpg',
        'facial': 'grooming.jpg',
        'electrical': 'electrical.jpg',
        'fan': 'electrical.jpg',
        'light': 'electrical.jpg',
        'wiring': 'electrical.jpg',
        'mcb': 'electrical.jpg',
        'ac': 'appliance.jpg',
        'refrigerator': 'appliance.jpg',
        'washing': 'appliance.jpg',
        'tv': 'appliance.jpg',
        'heater': 'appliance.jpg',
        'appliance': 'appliance.jpg',
    }

    services = Service.objects.all()
    count = 0

    for service in services:
        name_lower = service.name.lower()
        source_file = None
        
        # Try specific keywords first
        for key, filename in mapping.items():
            if key in name_lower:
                source_file = filename
                break
        
        # Fallback to category name if no keyword matched
        if not source_file:
            cat_name = service.category.name.lower()
            for key, filename in mapping.items():
                if key in cat_name:
                    source_file = filename
                    break
        
        # Final fallback
        if not source_file:
            source_file = 'handyman.jpg'

        source_path = os.path.join(static_img_dir, source_file)
        
        if os.path.exists(source_path):
            # Generate new name
            new_filename = f"{slugify(service.name)}.jpg"
            target_path = os.path.join(media_services_dir, new_filename)
            
            # Copy file
            shutil.copy2(source_path, target_path)
            
            # Update database record
            # We use the relative path for the ImageField
            service.image = f"services/{new_filename}"
            service.save()
            print(f"Updated {service.name} -> {service.image}")
            count += 1
        else:
            print(f"Warning: Source image {source_path} not found for {service.name}")

    print(f"\nSuccessfully migrated {count} service images to media/services/")

if __name__ == "__main__":
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_booking.settings')
    django.setup()
    migrate_images()
