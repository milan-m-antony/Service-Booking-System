from bookings.models import CustomUser
staff = CustomUser.objects.filter(role=CustomUser.Roles.STAFF)
print("--- Staff Service Assignment Audit ---")
for s in staff:
    services = list(s.services.all().values_list('name', flat=True))
    print(f"{s.username}: {services}")
