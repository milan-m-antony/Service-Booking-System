from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Booking, BookingFeedback, CustomUser, Service, ServiceCategory, StaffBlockedSlot, StaffLeaveDate, UserMessage


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Additional Info", {"fields": ("role", "phone", "avatar")}),)
    list_display = ("display_name", "email", "role", "is_staff", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")
    list_filter = ("role", "is_staff", "is_active")


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "color")
    search_fields = ("name",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "duration_minutes", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "description")
    filter_horizontal = ("staff",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("customer", "service", "staff", "scheduled_at", "status", "is_paid")
    list_filter = ("status", "is_paid", "scheduled_at")
    search_fields = ("customer__first_name", "customer__last_name", "service__name", "staff__first_name", "staff__last_name")


@admin.register(BookingFeedback)
class BookingFeedbackAdmin(admin.ModelAdmin):
    list_display = ("booking", "customer", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("booking__service__name", "customer__first_name", "customer__last_name", "comment")


@admin.register(StaffLeaveDate)
class StaffLeaveDateAdmin(admin.ModelAdmin):
    list_display = ("staff", "date", "note", "is_active")
    list_filter = ("is_active", "staff")
    search_fields = ("staff__first_name", "staff__last_name", "note")


@admin.register(StaffBlockedSlot)
class StaffBlockedSlotAdmin(admin.ModelAdmin):
    list_display = ("staff", "date", "time", "note", "is_active")
    list_filter = ("is_active", "staff", "date")
    search_fields = ("staff__first_name", "staff__last_name", "note")


@admin.register(UserMessage)
class UserMessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "recipient", "subject", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("sender__username", "recipient__username", "subject", "body")
