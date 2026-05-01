from django.utils import timezone

from .models import Booking, CustomUser, Service


def mobile_notifications(request):
    if not request.user.is_authenticated:
        return {"mobile_notifications": []}

    notifications = [
        {
            "title": "System",
            "message": "Keep your profile details updated for smoother bookings.",
            "type": "system",
        }
    ]

    user = request.user

    if user.role == CustomUser.Roles.CUSTOMER:
        upcoming = Booking.objects.filter(
            customer=user,
            status__in=[Booking.Status.PENDING, Booking.Status.IN_PROGRESS],
            scheduled_at__gte=timezone.now(),
        ).order_by("scheduled_at")
        count = upcoming.count()
        if count:
            next_item = upcoming.first()
            notifications.append(
                {
                    "title": "Service",
                    "message": f"{count} active booking(s). Next: {next_item.service.name} on {next_item.scheduled_at:%d %b, %I:%M %p}.",
                    "type": "service",
                }
            )
        else:
            notifications.append(
                {
                    "title": "Service",
                    "message": "No active bookings right now. You can book a new service.",
                    "type": "service",
                }
            )

    elif user.role == CustomUser.Roles.STAFF:
        today = timezone.localdate()
        today_jobs = Booking.objects.filter(staff=user, scheduled_at__date=today).exclude(status=Booking.Status.CANCELLED).count()
        pending = Booking.objects.filter(staff=user, status=Booking.Status.PENDING).count()
        notifications.append(
            {
                "title": "Service",
                "message": f"Today: {today_jobs} job(s). Pending updates: {pending}.",
                "type": "service",
            }
        )

    elif user.role == CustomUser.Roles.ADMIN:
        pending = Booking.objects.filter(status=Booking.Status.PENDING).count()
        inactive_services = Service.objects.filter(is_active=False).count()
        notifications.append(
            {
                "title": "Admin",
                "message": f"Pending bookings: {pending}. Inactive services: {inactive_services}.",
                "type": "service",
            }
        )

    return {"mobile_notifications": notifications}
