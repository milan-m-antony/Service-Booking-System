from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta


class CustomUser(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        STAFF = "staff", "Staff"
        CUSTOMER = "customer", "Customer"

    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.CUSTOMER)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    must_change_password = models.BooleanField(default=False)

    @property
    def display_name(self):
        full_name = self.get_full_name().strip()
        return full_name if full_name else self.username

    def __str__(self):
        return f"{self.display_name} ({self.role})"


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji or icon class")
    color = models.CharField(max_length=20, default="#34d399")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=120)
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="services")
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.PositiveIntegerField(default=60)
    image = models.ImageField(upload_to="services/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    staff = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="services",
        blank=True,
        limit_choices_to={"role": CustomUser.Roles.STAFF},
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_bookings",
        limit_choices_to={"role": CustomUser.Roles.CUSTOMER},
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="bookings")
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="staff_bookings",
        limit_choices_to={"role": CustomUser.Roles.STAFF},
    )
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    location_coords = models.TextField(blank=True)

    class Meta:
        ordering = ["-scheduled_at"]

    def _booking_window(self):
        if not self.scheduled_at or not self.service_id:
            return None, None
        start = self.scheduled_at
        end = start + timedelta(minutes=self.service.duration_minutes)
        return start, end

    def _interval_dates(self, start, end):
        if not start or not end:
            return []
        current = start.date()
        end_date = end.date()
        dates = []
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=1)
        return dates

    def clean(self):
        if self.scheduled_at and self.scheduled_at < timezone.now():
            raise ValidationError({"scheduled_at": "Bookings must be scheduled in the future."})

        if not self.staff_id or not self.service_id or not self.scheduled_at:
            return

        start, end = self._booking_window()
        interval_dates = self._interval_dates(start, end)

        if StaffLeaveDate.objects.filter(staff=self.staff, date__in=interval_dates, is_active=True).exists():
            raise ValidationError({"scheduled_at": "Selected staff is unavailable on one of the chosen dates."})

        blocked_slots = StaffBlockedSlot.objects.filter(
            staff=self.staff,
            date__in=interval_dates,
            is_active=True,
        )
        for slot in blocked_slots:
            slot_start = timezone.make_aware(
                datetime.combine(slot.date, slot.time),
                timezone.get_current_timezone(),
            )
            if start < slot_start + timedelta(minutes=1) and slot_start < end:
                raise ValidationError({"scheduled_at": "Selected time overlaps with a blocked staff slot."})

        for existing in Booking.objects.filter(staff=self.staff).exclude(pk=self.pk).exclude(status__in=[Booking.Status.CANCELLED, Booking.Status.COMPLETED]):
            existing_start = existing.scheduled_at
            existing_end = existing_start + timedelta(minutes=existing.service.duration_minutes)
            if start < existing_end and existing_start < end:
                raise ValidationError({"scheduled_at": "This staff member is already booked for an overlapping time."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer} - {self.service} @ {self.scheduled_at:%Y-%m-%d %H:%M}"


class BookingFeedback(models.Model):
    class Rating(models.IntegerChoices):
        ONE = 1, "1 - Poor"
        TWO = 2, "2 - Fair"
        THREE = 3, "3 - Good"
        FOUR = 4, "4 - Very Good"
        FIVE = 5, "5 - Excellent"

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="feedback")
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="booking_feedbacks",
        limit_choices_to={"role": CustomUser.Roles.CUSTOMER},
    )
    rating = models.PositiveSmallIntegerField(choices=Rating.choices)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if not self.booking_id or not self.customer_id:
            return
        if self.booking.customer_id != self.customer_id:
            raise ValidationError({"customer": "Feedback can only be added by the booking owner."})
        if self.booking.status != Booking.Status.COMPLETED:
            raise ValidationError({"booking": "Feedback is only allowed after the booking is completed."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.booking} - {self.rating}"


class StaffLeaveDate(models.Model):
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="leave_dates",
        limit_choices_to={"role": CustomUser.Roles.STAFF},
    )
    date = models.DateField()
    note = models.CharField(max_length=180, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["date"]
        unique_together = ("staff", "date")

    def __str__(self):
        suffix = f" - {self.note}" if self.note else ""
        return f"{self.staff.display_name}: {self.date:%Y-%m-%d}{suffix}"


class StaffBlockedSlot(models.Model):
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocked_slots",
        limit_choices_to={"role": CustomUser.Roles.STAFF},
    )
    date = models.DateField()
    time = models.TimeField()
    note = models.CharField(max_length=180, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["date", "time"]
        unique_together = ("staff", "date", "time")

    def __str__(self):
        suffix = f" - {self.note}" if self.note else ""
        return f"{self.staff.display_name}: {self.date:%Y-%m-%d} {self.time:%H:%M}{suffix}"


class UserMessage(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_messages",
    )
    subject = models.CharField(max_length=140, blank=True)
    body = models.TextField()
    preset_label = models.CharField(max_length=80, blank=True)
    is_read = models.BooleanField(default=False)
    sender_deleted = models.BooleanField(default=False)
    recipient_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender.display_name} to {self.recipient.display_name}"
