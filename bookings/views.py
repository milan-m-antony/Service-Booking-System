from datetime import datetime, timedelta
from decimal import Decimal
import random

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.http import JsonResponse
from django.db.utils import DatabaseError, OperationalError
from django.db.models import Avg, Count, Prefetch, Q
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .decorators import role_required
from .forms import BookingFeedbackForm, BookingForm, LoginForm, ProfileForm, RegisterForm
from .models import Booking, BookingFeedback, CustomUser, Service, ServiceCategory, StaffBlockedSlot, StaffLeaveDate, UserMessage


@login_required
@never_cache
def message_center(request):
    """Message center with presets and persistent inbox/sent messages."""
    presets = _message_presets_for_role(request.user.role)

    prefill_label = (request.GET.get("preset_label") or "").strip()
    prefill_recipient_id = request.GET.get("recipient_id", "")
    prefill_subject = (request.GET.get("subject") or "").strip()
    prefill_body = (request.GET.get("body") or "").strip()
    
    if prefill_recipient_id.isdigit():
        prefill_recipient_id = int(prefill_recipient_id)
    else:
        prefill_recipient_id = None

    if prefill_label and not prefill_body:
        preset_map = {item["key"]: item for item in presets}
        matched_preset = preset_map.get(prefill_label)
        if matched_preset:
            prefill_body = matched_preset["body"]
            if not prefill_subject:
                prefill_subject = matched_preset["subject"]

    try:
        recipients = CustomUser.objects.filter(is_active=True).exclude(id=request.user.id)
        if request.user.role == CustomUser.Roles.CUSTOMER:
            recipients = recipients.filter(role__in=[CustomUser.Roles.STAFF, CustomUser.Roles.ADMIN])
        elif request.user.role == CustomUser.Roles.STAFF:
            recipients = recipients.filter(role__in=[CustomUser.Roles.CUSTOMER, CustomUser.Roles.ADMIN])
        recipients = recipients.order_by("first_name", "last_name", "username")

        if request.method == "POST":
            action = (request.POST.get("action") or "").strip()
            selected_message_ids = [
                int(message_id)
                for message_id in request.POST.getlist("selected_message_ids")
                if message_id.isdigit()
            ]

            if action.startswith("delete_inbox_message:"):
                message_id = action.split(":", 1)[1]
                if not message_id.isdigit():
                    messages.warning(request, "Invalid inbox message.")
                    return redirect("messages")

                deleted_count = UserMessage.objects.filter(
                    id=int(message_id),
                    recipient=request.user,
                    recipient_deleted=False,
                ).update(recipient_deleted=True)
                if deleted_count:
                    _purge_fully_deleted_messages()
                    messages.success(request, "Inbox message deleted.")
                else:
                    messages.info(request, "Message was already removed.")
                return redirect("messages")

            if action.startswith("delete_sent_message:"):
                message_id = action.split(":", 1)[1]
                if not message_id.isdigit():
                    messages.warning(request, "Invalid sent message.")
                    return redirect("messages")

                deleted_count = UserMessage.objects.filter(
                    id=int(message_id),
                    sender=request.user,
                    sender_deleted=False,
                ).update(sender_deleted=True)
                if deleted_count:
                    _purge_fully_deleted_messages()
                    messages.success(request, "Sent message deleted.")
                else:
                    messages.info(request, "Message was already removed.")
                return redirect("messages")

            if action == "delete_inbox_selected":
                if not selected_message_ids:
                    messages.warning(request, "Select at least one inbox message to delete.")
                    return redirect("messages")

                deleted_count = UserMessage.objects.filter(
                    id__in=selected_message_ids,
                    recipient=request.user,
                    recipient_deleted=False,
                ).update(recipient_deleted=True)
                if deleted_count:
                    _purge_fully_deleted_messages()
                    messages.success(request, f"Deleted {deleted_count} inbox message(s).")
                else:
                    messages.info(request, "No inbox messages were deleted.")
                return redirect("messages")

            if action == "delete_sent_selected":
                if not selected_message_ids:
                    messages.warning(request, "Select at least one sent message to delete.")
                    return redirect("messages")

                deleted_count = UserMessage.objects.filter(
                    id__in=selected_message_ids,
                    sender=request.user,
                    sender_deleted=False,
                ).update(sender_deleted=True)
                if deleted_count:
                    _purge_fully_deleted_messages()
                    messages.success(request, f"Deleted {deleted_count} sent message(s).")
                else:
                    messages.info(request, "No sent messages were deleted.")
                return redirect("messages")

            if action == "delete_all_inbox":
                deleted_count = UserMessage.objects.filter(recipient=request.user, recipient_deleted=False).update(
                    recipient_deleted=True
                )
                if deleted_count:
                    _purge_fully_deleted_messages()
                    messages.success(request, f"Deleted all inbox messages ({deleted_count}).")
                else:
                    messages.info(request, "Inbox is already empty.")
                return redirect("messages")

            if action == "delete_all_sent":
                deleted_count = UserMessage.objects.filter(sender=request.user, sender_deleted=False).update(
                    sender_deleted=True
                )
                if deleted_count:
                    _purge_fully_deleted_messages()
                    messages.success(request, f"Deleted all sent messages ({deleted_count}).")
                else:
                    messages.info(request, "Sent items are already empty.")
                return redirect("messages")

            preset_label = (request.POST.get("preset_label") or "").strip()
            subject = (request.POST.get("subject") or "").strip()
            body = (request.POST.get("body") or "").strip()
            target_id = request.POST.get("recipient_id")

            recipient = recipients.filter(id=target_id).first() if target_id else None

            if not recipient:
                messages.error(request, "Please choose a valid recipient.")
            elif not body:
                messages.error(request, "Message body is required.")
            else:
                UserMessage.objects.create(
                    sender=request.user,
                    recipient=recipient,
                    subject=subject,
                    body=body,
                    preset_label=preset_label,
                )
                messages.success(request, f"Message sent to {recipient.display_name}.")
                return redirect("messages")

        unread_ids = list(
            UserMessage.objects.filter(recipient=request.user, is_read=False, recipient_deleted=False).values_list("id", flat=True)
        )
        if unread_ids:
            UserMessage.objects.filter(id__in=unread_ids).update(is_read=True)

        inbox_messages = (
            UserMessage.objects.filter(recipient=request.user, recipient_deleted=False)
            .select_related("sender")
            .order_by("-created_at")[:20]
        )
        sent_messages = (
            UserMessage.objects.filter(sender=request.user, sender_deleted=False)
            .select_related("recipient")
            .order_by("-created_at")[:20]
        )

        context = {
            "presets": presets,
            "recipients": recipients,
            "inbox_messages": inbox_messages,
            "sent_messages": sent_messages,
            "inbox_count": UserMessage.objects.filter(recipient=request.user, recipient_deleted=False).count(),
            "sent_count": UserMessage.objects.filter(sender=request.user, sender_deleted=False).count(),
            "unread_count": len(unread_ids),
            "prefill_label": prefill_label,
            "prefill_recipient_id": prefill_recipient_id,
            "prefill_subject": prefill_subject,
            "prefill_body": prefill_body,
        }
        return render(request, "bookings/message_center.html", context)
    except (OperationalError, DatabaseError):
        if request.method == "POST":
            messages.error(request, "Message service is temporarily unavailable. Please try again.")
            return redirect("messages")

        context = {
            "presets": presets,
            "recipients": [],
            "inbox_messages": [],
            "sent_messages": [],
            "inbox_count": 0,
            "sent_count": 0,
            "unread_count": 0,
            "prefill_label": prefill_label,
            "prefill_recipient_id": prefill_recipient_id,
            "prefill_subject": prefill_subject,
            "prefill_body": prefill_body,
        }
        return render(request, "bookings/message_center.html", context)


def _dashboard_name_for(user):
    if user.role == CustomUser.Roles.ADMIN:
        return "admin_dashboard"
    if user.role == CustomUser.Roles.STAFF:
        return "staff_dashboard"
    return "user_dashboard"


def _message_presets_for_role(role):
    if role == CustomUser.Roles.CUSTOMER:
        return [
            {"key": "booking_request", "label": "Booking request", "subject": "Booking request", "body": "Hello, I would like to book a service. Please share availability and next steps."},
            {"key": "availability", "label": "Availability check", "subject": "Availability check", "body": "Are you available on a specific date or time slot?"},
            {"key": "pricing", "label": "Pricing question", "subject": "Pricing question", "body": "Can you confirm the price for this service and any extra charges?"},
        ]
    if role == CustomUser.Roles.STAFF:
        return [
            {"key": "job_update", "label": "Job update", "subject": "Job update", "body": "Hello, I am sending a quick update on the job status and timing."},
            {"key": "availability_notice", "label": "Availability notice", "subject": "Availability notice", "body": "Please confirm your preferred time so I can check my schedule."},
            {"key": "follow_up", "label": "Follow up", "subject": "Follow up", "body": "Thanks for your booking. Please reply if you need any changes or support."},
        ]
    return [
        {"key": "review_request", "label": "Review request", "subject": "Review request", "body": "Please review the latest booking updates and confirm if any action is needed."},
        {"key": "system_notice", "label": "System notice", "subject": "System notice", "body": "A booking or message status has changed. Please review the dashboard for updates."},
        {"key": "follow_up", "label": "Follow up", "subject": "Follow up", "body": "Please follow up on any pending items or unanswered messages."},
    ]


def _dashboard_quick_presets_for_role(role):
    if role == CustomUser.Roles.CUSTOMER:
        return [
            {"key": "book", "label": "Book service", "subject": "Booking request", "body": "Hello, I would like to book a service."},
            {"key": "reschedule", "label": "Reschedule", "subject": "Reschedule request", "body": "I need to change my booking date or time. Please help me reschedule."},
        ]
    if role == CustomUser.Roles.STAFF:
        return [
            {"key": "update", "label": "Job update", "subject": "Job update", "body": "I am sending a quick status update for the assigned job."},
            {"key": "availability", "label": "Availability", "subject": "Availability check", "body": "Please confirm the preferred time so I can align my schedule."},
        ]
    return [
        {"key": "notice", "label": "Notice", "subject": "Admin notice", "body": "Please review the dashboard for the latest updates and pending items."},
        {"key": "review", "label": "Review request", "subject": "Review request", "body": "Please review the pending bookings and respond when ready."},
    ]


def _purge_fully_deleted_messages():
    UserMessage.objects.filter(sender_deleted=True, recipient_deleted=True).delete()


def _dashboard_message_context(user, limit=5):
    try:
        unread_count = UserMessage.objects.filter(recipient=user, is_read=False, recipient_deleted=False).count()
        inbox_count = UserMessage.objects.filter(recipient=user, recipient_deleted=False).count()
        sent_count = UserMessage.objects.filter(sender=user, sender_deleted=False).count()
        recent_messages = (
            UserMessage.objects.filter(Q(recipient=user, recipient_deleted=False) | Q(sender=user, sender_deleted=False))
            .select_related("sender", "recipient")
            .order_by("-created_at")[:limit]
        )
    except (OperationalError, DatabaseError):
        unread_count = 0
        inbox_count = 0
        sent_count = 0
        recent_messages = []

    return {
        "dashboard_unread_count": unread_count,
        "dashboard_inbox_count": inbox_count,
        "dashboard_sent_count": sent_count,
        "dashboard_messages": recent_messages,
        "dashboard_message_presets": _dashboard_quick_presets_for_role(user.role),
    }


def home(request):
    if request.user.is_authenticated:
        return redirect("role_dashboard")

    categories = (
        ServiceCategory.objects.annotate(
            active_service_count=Count("services", filter=Q(services__is_active=True), distinct=True)
        )
        .prefetch_related("services")
        .order_by("name")
    )
    services = (
        Service.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("staff")
        .annotate(
            avg_rating=Avg("bookings__feedback__rating"),
            review_count=Count("bookings__feedback", distinct=True),
        )
    )
    return render(
        request,
        "bookings/home.html",
        {
            "categories": categories,
            "services": services,
            "random_seed": random.randint(1000, 999999),
            "is_guest_home": True,
        },
    )


def filter_services(request):
    category_id = request.GET.get("category")
    query = request.GET.get("query")
    mode = request.GET.get("mode")
    
    services = (
        Service.objects.filter(is_active=True)
        .select_related("category")
        .annotate(
            avg_rating=Avg("bookings__feedback__rating"),
            review_count=Count("bookings__feedback", distinct=True),
        )
    )
    
    if category_id and category_id != "all":
        services = services.filter(category_id=category_id)
        
    if query:
        services = services.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )

    if mode == "suggestions":
        from django.http import JsonResponse
        results = []
        for s in services[:5]:
            results.append({
                "id": s.id,
                "name": s.name,
                "category": s.category.name,
                "image_url": s.image.url if s.image else "/static/bookings/img/service-placeholder.jpg"
            })
        return JsonResponse(results, safe=False)
        
    return render(request, "bookings/services_list.html", {"services": services})


def professional_staff(request):
    staff_members = (
        CustomUser.objects.filter(role=CustomUser.Roles.STAFF, is_active=True)
        .annotate(
            completed_jobs=Count(
                "staff_bookings",
                filter=Q(staff_bookings__status=Booking.Status.COMPLETED),
                distinct=True,
            ),
            avg_rating=Avg("staff_bookings__feedback__rating"),
            rating_count=Count("staff_bookings__feedback", distinct=True),
        )
        .prefetch_related(
            Prefetch("services", queryset=Service.objects.filter(is_active=True).order_by("name"))
        )
        .order_by("-completed_jobs", "-rating_count", "first_name", "last_name", "username")
    )
    return render(
        request,
        "bookings/professional_staff.html",
        {
            "staff_members": staff_members,
            "random_seed": random.randint(1000, 999999),
        },
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect("role_dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your account is ready.")
            return redirect("role_dashboard")
    else:
        form = RegisterForm()

    return render(request, "bookings/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("role_dashboard")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Signed in successfully.")
            if user.must_change_password:
                return redirect("force_password_change")
            return redirect("role_dashboard")
    else:
        form = LoginForm(request)

    return render(request, "bookings/login.html", {"form": form})


@never_cache
def logout_view(request):
    logout(request)
    request.session.flush()
    messages.info(request, "You have signed out.")
    return redirect("home")


@login_required
@never_cache
def role_dashboard(request):
    if request.user.must_change_password:
        return redirect("force_password_change")
    
    # Get the target dashboard view name based on role
    target_view = _dashboard_name_for(request.user)
    
    # Construct the redirect URL with preserved query parameters
    url = reverse(target_view)
    query_string = request.GET.urlencode()
    if query_string:
        url = f"{url}?{query_string}"
    
    return redirect(url)


@login_required
def global_search(request):
    query = (request.GET.get("q") or "").strip()
    next_url = (request.GET.get("next") or "").strip()

    if not query:
        if next_url and not next_url.startswith("/search/"):
            return redirect(next_url)
        return redirect("role_dashboard")

    services = Service.objects.none()
    staff_members = CustomUser.objects.none()
    bookings = Booking.objects.none()

    services = (
        Service.objects.select_related("category")
        .filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
        )
        .order_by("name")[:12]
    )

    staff_members = (
        CustomUser.objects.filter(role=CustomUser.Roles.STAFF)
        .filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )
        .order_by("first_name", "last_name", "username")[:12]
    )

    bookings_base = Booking.objects.select_related("service", "staff", "customer")
    if request.user.role == CustomUser.Roles.CUSTOMER:
        bookings_base = bookings_base.filter(customer=request.user)
    elif request.user.role == CustomUser.Roles.STAFF:
        bookings_base = bookings_base.filter(staff=request.user)

    bookings = (
        bookings_base.filter(
            Q(service__name__icontains=query)
            | Q(staff__first_name__icontains=query)
            | Q(staff__last_name__icontains=query)
            | Q(customer__first_name__icontains=query)
            | Q(customer__last_name__icontains=query)
            | Q(status__icontains=query)
        )
        .order_by("-scheduled_at")[:12]
    )

    context = {
        "query": query,
        "services": services,
        "staff_members": staff_members,
        "bookings": bookings,
    }
    return render(request, "bookings/search_results.html", context)


@login_required
def force_password_change(request):
    if not request.user.must_change_password:
        return redirect("role_dashboard")

    if request.method == "POST":
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.must_change_password = False
            user.save(update_fields=["password", "must_change_password"])
            login(request, user)
            messages.success(request, "Password updated successfully.")
            return redirect("role_dashboard")
    else:
        form = SetPasswordForm(request.user)

    return render(request, "bookings/force_password_change.html", {"form": form})


@role_required(CustomUser.Roles.CUSTOMER)
def booking_create(request):
    if request.method == "POST":
        form = BookingForm(request.POST, user=request.user)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.customer = request.user
            booking.save()
            messages.success(request, "Booking created successfully.")
            return redirect(_dashboard_name_for(request.user))
    else:
        form = BookingForm(user=request.user)

    services = Service.objects.filter(is_active=True).select_related("category").prefetch_related("staff")
    categories = ServiceCategory.objects.filter(services__is_active=True).distinct().order_by("name")
    staff_leave_rows = StaffLeaveDate.objects.filter(is_active=True).values("staff_id", "date")
    staff_slot_rows = StaffBlockedSlot.objects.filter(is_active=True).values("staff_id", "date", "time")
    booked_slot_rows = Booking.objects.exclude(status=Booking.Status.CANCELLED).values("staff_id", "scheduled_at")

    staff_blocked_dates = {}
    for row in staff_leave_rows:
        staff_key = str(row["staff_id"])
        staff_blocked_dates.setdefault(staff_key, []).append(row["date"].isoformat())

    staff_blocked_slots = {}
    for row in staff_slot_rows:
        staff_key = str(row["staff_id"])
        date_key = row["date"].isoformat()
        staff_blocked_slots.setdefault(staff_key, {}).setdefault(date_key, []).append(
            row["time"].strftime("%H:%M")
        )

    staff_booked_slots = {}
    for row in booked_slot_rows:
        staff_id = row.get("staff_id")
        scheduled_at = row.get("scheduled_at")
        if not staff_id or not scheduled_at:
            continue
        staff_key = str(staff_id)
        date_key = scheduled_at.date().isoformat()
        time_key = scheduled_at.strftime("%H:%M")
        staff_booked_slots.setdefault(staff_key, {}).setdefault(date_key, []).append(time_key)

    services_payload = [
        {
            "id": service.id,
            "name": service.name,
            "category_id": service.category_id,
            "category_name": service.category.name,
            "price": str(service.price),
            "duration": service.duration_minutes,
            "description": service.description or "Professional and reliable service.",
            "staff": [
                {"id": member.id, "display_name": member.display_name}
                for member in service.staff.all()
            ],
        }
        for service in services
    ]

    context = {
        "form": form,
        "categories": categories,
        "services": services,
        "services_payload": services_payload,
        "staff_blocked_dates": staff_blocked_dates,
        "staff_blocked_slots": staff_blocked_slots,
        "staff_booked_slots": staff_booked_slots,
    }
    return render(request, "bookings/booking_create.html", context)


@login_required
@never_cache
def user_dashboard(request):
    active_tab = request.GET.get("tab", "overview")
    
    bookings = (
        Booking.objects.filter(customer=request.user)
        .select_related("service", "staff")
        .order_by("-scheduled_at")
    )
    
    # Calendar Data Logic
    selected_date_str = request.GET.get("slot_date", timezone.localdate().isoformat())
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except ValueError:
        selected_date = timezone.localdate()

    user_calendar_data = {}
    status_priority = {'pending': 3, 'confirmed': 2, 'in_progress': 2, 'completed': 1, 'cancelled': 0}
    
    for b in bookings.order_by('scheduled_at'):
        d_iso = b.scheduled_at.date().isoformat()
        current_status = b.status
        
        if current_status == 'cancelled':
            continue
            
        if d_iso not in user_calendar_data or status_priority.get(current_status, 0) > status_priority.get(user_calendar_data[d_iso]['status'], 0):
            user_calendar_data[d_iso] = {
                "status": current_status, 
                "has_booking": True
            }
    
    selected_date_bookings = bookings.filter(scheduled_at__date=selected_date)

    feedback_map = {
        item.booking_id: item
        for item in BookingFeedback.objects.filter(customer=request.user, booking__in=bookings)
    }
    for booking in bookings:
        booking.feedback_entry = feedback_map.get(booking.id)

    total_spent = sum(booking.service.price for booking in bookings if booking.status == Booking.Status.COMPLETED)
    context = {
        "bookings": bookings,
        "total_bookings": bookings.count(),
        "active_bookings": bookings.filter(status__in=[Booking.Status.PENDING, Booking.Status.IN_PROGRESS]).count(),
        "total_spent": total_spent if isinstance(total_spent, Decimal) else Decimal("0.00"),
        "active_tab": active_tab,
        "selected_slot_date": selected_date.isoformat(),
        "selected_date_bookings": selected_date_bookings,
        "user_calendar_data": user_calendar_data,
        "today": timezone.localdate().isoformat(),
    }
    context.update(_dashboard_message_context(request.user))
    return render(request, "bookings/user_dashboard.html", context)


@role_required(CustomUser.Roles.STAFF)
@never_cache
def staff_dashboard(request):
    return _render_staff_dashboard(request, view_mode="home")


@role_required(CustomUser.Roles.STAFF)
def staff_availability(request):
    return _render_staff_dashboard(request, view_mode="availability")


def _render_staff_dashboard(request, view_mode="home"):
    active_tab = request.GET.get("tab", "overview")
    # map view_mode to active_tab for backward compatibility if needed
    if view_mode == "availability":
        active_tab = "availability"
    
    redirect_name = "staff_availability" if view_mode == "availability" else "staff_dashboard"
    ajax_mode = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax") == "1"
    selected_slot_date_override = None
    ajax_success = True
    ajax_message = ""
    time_slot_options = [
        "09:00", "10:00", "11:00", "12:00", "13:00",
        "14:00", "15:00", "16:00", "17:00", "18:00",
    ]

    def _redirect_with_slot_date(date_value=None):
        url = reverse(redirect_name)
        if date_value:
            return redirect(f"{url}?slot_date={date_value}")
        return redirect(url)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "toggle_leave_date":
            raw_date = request.POST.get("leave_date", "").strip()
            if raw_date:
                try:
                    date_obj = datetime.strptime(raw_date, "%Y-%m-%d").date()
                    if date_obj < timezone.localdate():
                        messages.error(request, "Cannot update past dates.")
                        ajax_success = False
                        ajax_message = "Cannot update past dates."
                    else:
                        existing_leave = StaffLeaveDate.objects.filter(
                            staff=request.user,
                            date=date_obj,
                            is_active=True,
                        ).first()
                        if existing_leave:
                            existing_leave.delete()
                            messages.success(request, "Selected date is now available.")
                            ajax_message = "Selected date is now available."
                        else:
                            active_bookings = Booking.objects.filter(
                                staff=request.user,
                                scheduled_at__date=date_obj,
                            ).exclude(status=Booking.Status.CANCELLED).count()
                            StaffLeaveDate.objects.create(
                                staff=request.user,
                                date=date_obj,
                                is_active=True,
                            )
                            if active_bookings:
                                messages.warning(request, f"Date blocked. Note: {active_bookings} booking(s) already exist on this date.")
                                ajax_message = f"Date blocked. Note: {active_bookings} booking(s) already exist on this date."
                            else:
                                messages.success(request, "Selected date is now blocked.")
                                ajax_message = "Selected date is now blocked."
                except ValueError:
                    messages.error(request, "Invalid date.")
                    ajax_success = False
                    ajax_message = "Invalid date."
            else:
                messages.error(request, "Please choose a valid date.")
                ajax_success = False
                ajax_message = "Please choose a valid date."

            if ajax_mode:
                selected_slot_date_override = raw_date or timezone.localdate().isoformat()
            else:
                return _redirect_with_slot_date(raw_date or None)

        if action == "toggle_blocked_slot":
            raw_date = request.POST.get("slot_date", "").strip()
            raw_time = request.POST.get("slot_time", "").strip()
            if raw_date and raw_time:
                try:
                    date_obj = datetime.strptime(raw_date, "%Y-%m-%d").date()
                    time_obj = datetime.strptime(raw_time, "%H:%M").time()
                    if date_obj < timezone.localdate():
                        messages.error(request, "Cannot update slots for past dates.")
                        ajax_success = False
                        ajax_message = "Cannot update slots for past dates."
                    else:
                        has_booking = Booking.objects.filter(
                            staff=request.user,
                            scheduled_at__date=date_obj,
                            scheduled_at__time=time_obj,
                        ).exclude(status=Booking.Status.CANCELLED).exists()

                        if has_booking:
                            messages.error(request, "This slot already has a booking and cannot be blocked.")
                            ajax_success = False
                            ajax_message = "This slot already has a booking and cannot be blocked."
                        else:
                            existing_slot = StaffBlockedSlot.objects.filter(
                                staff=request.user,
                                date=date_obj,
                                time=time_obj,
                                is_active=True,
                            ).first()
                            if existing_slot:
                                existing_slot.delete()
                                messages.success(request, "Slot is now available.")
                                ajax_message = "Slot is now available."
                            else:
                                StaffBlockedSlot.objects.create(
                                    staff=request.user,
                                    date=date_obj,
                                    time=time_obj,
                                    is_active=True,
                                )
                                messages.success(request, "Slot blocked successfully.")
                                ajax_message = "Slot blocked successfully."
                except ValueError:
                    messages.error(request, "Invalid date or time.")
                    ajax_success = False
                    ajax_message = "Invalid date or time."
            else:
                messages.error(request, "Missing date/time to toggle slot.")
                ajax_success = False
                ajax_message = "Missing date/time to toggle slot."

            if ajax_mode:
                selected_slot_date_override = raw_date or timezone.localdate().isoformat()
            else:
                return _redirect_with_slot_date(raw_date or None)

        if action == "add_leave_date":
            raw_date = request.POST.get("leave_date", "").strip()
            note = request.POST.get("leave_note", "").strip()
            if raw_date:
                try:
                    date_obj = datetime.strptime(raw_date, "%Y-%m-%d").date()
                    if date_obj < timezone.localdate():
                        messages.error(request, "Cannot add past leave dates.")
                    else:
                        StaffLeaveDate.objects.update_or_create(
                            staff=request.user,
                            date=date_obj,
                            defaults={"note": note, "is_active": True},
                        )
                        messages.success(request, "Leave date saved.")
                except ValueError:
                    messages.error(request, "Invalid leave date.")
            else:
                messages.error(request, "Please choose a leave date.")
            return _redirect_with_slot_date(raw_date or None)

        if action == "remove_leave_date":
            leave_id = request.POST.get("leave_id")
            leave = StaffLeaveDate.objects.filter(id=leave_id, staff=request.user).first()
            if leave:
                leave.delete()
                messages.info(request, "Leave date removed.")
            return _redirect_with_slot_date(leave.date.isoformat() if leave else None)

        if action == "add_blocked_slot":
            raw_date = request.POST.get("slot_date", "").strip()
            raw_time = request.POST.get("slot_time", "").strip()
            note = request.POST.get("slot_note", "").strip()
            if raw_date and raw_time:
                try:
                    date_obj = datetime.strptime(raw_date, "%Y-%m-%d").date()
                    time_obj = datetime.strptime(raw_time, "%H:%M").time()
                    if date_obj < timezone.localdate():
                        messages.error(request, "Cannot block time slots for past dates.")
                    else:
                        StaffBlockedSlot.objects.update_or_create(
                            staff=request.user,
                            date=date_obj,
                            time=time_obj,
                            defaults={"note": note, "is_active": True},
                        )
                        messages.success(request, "Blocked time slot saved.")
                except ValueError:
                    messages.error(request, "Invalid date or time slot.")
            else:
                messages.error(request, "Please select both date and time slot.")
            return _redirect_with_slot_date(raw_date or None)

        if action == "remove_blocked_slot":
            slot_id = request.POST.get("slot_id")
            slot = StaffBlockedSlot.objects.filter(id=slot_id, staff=request.user).first()
            if slot:
                slot.delete()
                messages.info(request, "Blocked slot removed.")
            return _redirect_with_slot_date(slot.date.isoformat() if slot else None)

    bookings = Booking.objects.filter(staff=request.user).select_related("customer", "service")
    leave_dates = StaffLeaveDate.objects.filter(staff=request.user, is_active=True).order_by("date")
    blocked_slots = StaffBlockedSlot.objects.filter(staff=request.user, is_active=True).order_by("date", "time")

    selected_slot_date_raw = (selected_slot_date_override or request.GET.get("slot_date", "")).strip()
    if selected_slot_date_raw:
        try:
            selected_slot_date = datetime.strptime(selected_slot_date_raw, "%Y-%m-%d").date()
        except ValueError:
            selected_slot_date = timezone.localdate()
    else:
        selected_slot_date = timezone.localdate()

    marked_slots_for_date = []
    marked_slot_times = set()
    blocked_slot_times = set()
    booked_slot_times = set()

    blocked_on_date = blocked_slots.filter(date=selected_slot_date)
    for slot in blocked_on_date:
        slot_time = slot.time.strftime("%H:%M")
        marked_slot_times.add(slot_time)
        blocked_slot_times.add(slot_time)
        marked_slots_for_date.append(
            {
                "time": slot_time,
                "display": slot.time.strftime("%I:%M %p"),
                "type": "blocked",
                "note": slot.note,
            }
        )

    booked_on_date = bookings.filter(
        scheduled_at__date=selected_slot_date,
    ).exclude(
        status=Booking.Status.CANCELLED,
    )
    for booking in booked_on_date:
        slot_time = booking.scheduled_at.strftime("%H:%M")
        booked_slot_times.add(slot_time)
        if slot_time in marked_slot_times:
            continue
        marked_slot_times.add(slot_time)
        marked_slots_for_date.append(
            {
                "time": slot_time,
                "display": booking.scheduled_at.strftime("%I:%M %p"),
                "type": "booked",
                "note": booking.service.name,
            }
        )

    leave_date_set = set(leave_dates.values_list("date", flat=True))
    daily_unavailable_slots = {}

    for slot in blocked_slots:
        day_iso = slot.date.isoformat()
        slot_set = daily_unavailable_slots.setdefault(day_iso, set())
        slot_set.add(slot.time.strftime("%H:%M"))

    days_with_bookings = set()
    for booking in bookings.exclude(status=Booking.Status.CANCELLED).values_list("scheduled_at", flat=True):
        if not booking:
            continue
        day_iso = booking.date().isoformat()
        days_with_bookings.add(day_iso)
        slot_set = daily_unavailable_slots.setdefault(day_iso, set())
        slot_set.add(booking.strftime("%H:%M"))

    total_slots_per_day = len(time_slot_options)
    staff_calendar_data = {}

    for leave_date in leave_date_set:
        day_iso = leave_date.isoformat()
        staff_calendar_data[day_iso] = {
            "count": total_slots_per_day,
            "status": "closed",
            "has_booking": day_iso in days_with_bookings,
        }

    for day_iso, slot_set in daily_unavailable_slots.items():
        if day_iso in staff_calendar_data:
            # Already handled by leave_date but might need has_booking update
            if day_iso in days_with_bookings:
                staff_calendar_data[day_iso]["has_booking"] = True
            continue

        unavailable_count = len(slot_set)
        if unavailable_count <= 0:
            continue

        staff_calendar_data[day_iso] = {
            "count": unavailable_count,
            "status": "booked-out" if unavailable_count >= total_slots_per_day else "partial",
            "has_booking": day_iso in days_with_bookings,
        }

    available_slots_for_date = []
    if selected_slot_date not in leave_date_set:
        available_slots_for_date = [
            {
                "time": slot,
                "display": datetime.strptime(slot, "%H:%M").strftime("%I:%M %p"),
            }
            for slot in time_slot_options
            if slot not in marked_slot_times
        ]

    marked_slots_for_date.sort(key=lambda item: item["time"])

    total_earnings = sum(booking.service.price for booking in bookings if booking.status == Booking.Status.COMPLETED)

    context = {
        "bookings": bookings.order_by("scheduled_at"),
        "total_jobs": bookings.count(),
        "pending_count": bookings.filter(status=Booking.Status.PENDING).count(),
        "completed_count": bookings.filter(status=Booking.Status.COMPLETED).count(),
        "total_earnings": total_earnings if isinstance(total_earnings, (Decimal, int, float)) else 0,
        "leave_dates": leave_dates,
        "blocked_slots": blocked_slots,
        "today": timezone.localdate().isoformat(),
        "staff_view_mode": view_mode,

        "time_slot_options": time_slot_options,
        "marked_slots_for_date": marked_slots_for_date,
        "marked_slot_times": sorted(marked_slot_times),
        "blocked_slot_times": sorted(blocked_slot_times),
        "booked_slot_times": sorted(booked_slot_times),
        "available_slots_for_date": available_slots_for_date,
        "is_leave_date_selected": selected_slot_date in leave_date_set,
        "selected_date_bookings": booked_on_date.order_by("scheduled_at"),
        "staff_calendar_data": staff_calendar_data,
        "active_tab": active_tab,
    }
    context.update(_dashboard_message_context(request.user))

    if ajax_mode:
        return JsonResponse(
            {
                "ok": ajax_success,
                "message": ajax_message,
                "selected_slot_date": selected_slot_date.isoformat(),
                "selected_slot_date_display": selected_slot_date.strftime("%d %b %Y"),
                "is_leave_date_selected": selected_slot_date in leave_date_set,
                "jobs_count": booked_on_date.count(),
                "blocked_slot_times": sorted(blocked_slot_times),
                "booked_slot_times": sorted(booked_slot_times),
                "selected_date_bookings": [
                    {
                        "time": booking.scheduled_at.strftime("%I:%M %p"),
                        "service": booking.service.name,
                        "customer": booking.customer.display_name,
                        "status": booking.get_status_display(),
                    }
                    for booking in booked_on_date.order_by("scheduled_at")
                ],
                "leave_dates": [
                    {
                        "display": leave.date.strftime("%a, %d %b %Y"),
                        "status": "Blocked",
                    }
                    for leave in leave_dates
                ],
                "staff_calendar_data": staff_calendar_data,
            }
        )

    return render(request, "bookings/staff_dashboard.html", context)


@role_required(CustomUser.Roles.ADMIN)
@never_cache
def admin_dashboard(request):
    active_tab = request.GET.get("tab", "overview")
    bookings = Booking.objects.select_related("customer", "service", "staff").order_by("-scheduled_at")
    pending_bookings = bookings.filter(status=Booking.Status.PENDING)
    completed_bookings = bookings.filter(status=Booking.Status.COMPLETED)
    today = timezone.localdate()

    completed_revenue = sum(item.service.price for item in completed_bookings)

    context = {
        "bookings": bookings,
        "all_bookings": bookings,
        "total_bookings": bookings.count(),
        "pending_count": pending_bookings.count(),
        "completed_count": completed_bookings.count(),
        "cancelled_count": bookings.filter(status=Booking.Status.CANCELLED).count(),
        "today_bookings": bookings.filter(scheduled_at__date=today).count(),
        "completed_revenue": completed_revenue,
        "pending_bookings": pending_bookings[:8],
        "recent_bookings": bookings[:8],
        "active_tab": active_tab,
    }
    context.update(_dashboard_message_context(request.user))
    return render(request, "bookings/admin_dashboard.html", context)


@role_required(CustomUser.Roles.ADMIN)
@never_cache
def admin_categories(request):
    if request.method == "POST":
        action = request.POST.get("action", "create")
        name = request.POST.get("name", "").strip()
        icon = request.POST.get("icon", "").strip()
        color = request.POST.get("color", "#34d399").strip() or "#34d399"

        if action == "delete":
            cat_id = request.POST.get("category_id")
            category = ServiceCategory.objects.filter(id=cat_id).first()
            if category:
                category.delete()
                messages.success(request, f"Category '{category.name}' deleted.")
            else:
                messages.error(request, "Category not found.")
            return redirect("admin_categories")

        if action == "edit":
            cat_id = request.POST.get("category_id")
            category = ServiceCategory.objects.filter(id=cat_id).first()
            if category and name:
                category.name = name
                category.icon = icon
                category.color = color
                category.save()
                messages.success(request, f"Category '{category.name}' updated.")
            else:
                messages.error(request, "Category name is required.")
            return redirect("admin_categories")

        # Default: create
        if name:
            _, created = ServiceCategory.objects.get_or_create(
                name=name,
                defaults={"icon": icon, "color": color},
            )
            if created:
                messages.success(request, "Category added.")
            else:
                messages.info(request, "Category already exists.")
        else:
            messages.error(request, "Category name is required.")
        return redirect("admin_categories")

    categories = ServiceCategory.objects.all()
    return render(request, "bookings/admin_categories.html", {"categories": categories})


@role_required(CustomUser.Roles.ADMIN)
@never_cache
def admin_services(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            name = request.POST.get("name", "").strip()
            category_id = request.POST.get("category")
            description = request.POST.get("description", "").strip()
            price_raw = request.POST.get("price", "").strip()
            duration_raw = request.POST.get("duration", "").strip() or "60"

            try:
                category = ServiceCategory.objects.get(id=category_id)
                price = Decimal(price_raw)
                duration = int(duration_raw)
                if not name:
                    raise ValueError
                Service.objects.create(
                    name=name,
                    category=category,
                    description=description,
                    price=price,
                    duration_minutes=duration,
                    is_active=True,
                )
                messages.success(request, "Service added.")
            except Exception:
                messages.error(request, "Please provide valid service details.")

        if action == "toggle_active":
            service_id = request.POST.get("service_id")
            service = Service.objects.filter(id=service_id).first()
            if service:
                service.is_active = not service.is_active
                service.save(update_fields=["is_active"])
                messages.success(request, "Service status updated.")

        if action == "assign_staff":
            service_id = request.POST.get("service_id")
            staff_ids = request.POST.getlist("staff_ids")
            service = Service.objects.filter(id=service_id).first()
            if service:
                staff_qs = CustomUser.objects.filter(id__in=staff_ids, role=CustomUser.Roles.STAFF)
                service.staff.set(staff_qs)
                messages.success(request, f"Staff assignments updated for {service.name}.")
            else:
                messages.error(request, "Service not found.")

        return redirect("admin_services")

    services = Service.objects.select_related("category").prefetch_related("staff")
    categories = ServiceCategory.objects.all()
    staff_users = CustomUser.objects.filter(role=CustomUser.Roles.STAFF).order_by("first_name", "last_name", "username")
    return render(
        request,
        "bookings/admin_services.html",
        {"services": services, "categories": categories, "staff_users": staff_users},
    )


@role_required(CustomUser.Roles.ADMIN)
@never_cache
def admin_users(request):
    if request.method == "POST":
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")
        target_user = CustomUser.objects.filter(id=user_id).first()

        if action == "create_staff":
            first_name = request.POST.get("first_name", "").strip()
            last_name = request.POST.get("last_name", "").strip()
            email = request.POST.get("email", "").strip().lower()
            phone = request.POST.get("phone", "").strip()
            temp_password = request.POST.get("temp_password", "").strip()

            if not first_name or not email or not temp_password:
                messages.error(request, "First name, email, and temporary password are required.")
                return redirect("admin_users")

            if CustomUser.objects.filter(email__iexact=email).exists():
                messages.error(request, "A user with this email already exists.")
                return redirect("admin_users")

            base_username = slugify(" ".join(filter(None, [first_name, last_name]))) or slugify(email.split("@")[0]) or "staff"
            candidate = base_username
            suffix = 1
            while CustomUser.objects.filter(username=candidate).exists():
                candidate = f"{base_username}{suffix}"
                suffix += 1

            staff_user = CustomUser(
                username=candidate,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                role=CustomUser.Roles.STAFF,
                is_active=True,
                must_change_password=True,
            )
            staff_user.set_password(temp_password)
            staff_user.save()
            messages.success(request, f"Staff account created for {staff_user.display_name}. Temporary password must be changed on first login.")
            return redirect("admin_users")

        if target_user:
            if action == "set_role":
                role = request.POST.get("role")
                if role in CustomUser.Roles.values:
                    target_user.role = role
                    target_user.save(update_fields=["role"])
                    messages.success(request, "User role updated.")

            elif action == "toggle_active":
                target_user.is_active = not target_user.is_active
                target_user.save(update_fields=["is_active"])
                messages.success(request, "User status updated.")

            elif action == "delete_user":
                if target_user.id == request.user.id:
                    messages.error(request, "You cannot delete your own account.")
                else:
                    name = target_user.display_name
                    target_user.delete()
                    messages.success(request, f"User '{name}' has been permanently deleted.")

        return redirect("admin_users")

    users = CustomUser.objects.all().order_by("first_name", "last_name", "username")
    return render(request, "bookings/admin_users.html", {"users": users})


@role_required(CustomUser.Roles.STAFF, CustomUser.Roles.ADMIN)
@require_POST
def update_booking_status(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.user.role == CustomUser.Roles.STAFF and booking.staff_id != request.user.id:
        messages.error(request, "You can only update bookings assigned to you.")
        return redirect("staff_dashboard")

    new_status = request.POST.get("status")
    if new_status not in Booking.Status.values:
        messages.error(request, "Invalid status.")
        return redirect(_dashboard_name_for(request.user))

    if new_status == Booking.Status.COMPLETED and booking.status != Booking.Status.COMPLETED:
        booking.status = new_status
        booking.save(update_fields=["status"])
        messages.success(request, "Booking marked as completed.")
        return redirect(_dashboard_name_for(request.user))

    booking.status = new_status
    booking.save(update_fields=["status"])
    messages.success(request, "Booking status updated.")
    return redirect(_dashboard_name_for(request.user))


@role_required(CustomUser.Roles.CUSTOMER)
def booking_feedback(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related("service", "staff"), id=booking_id, customer=request.user)

    if booking.status != Booking.Status.COMPLETED:
        messages.error(request, "You can only review a completed booking.")
        return redirect("user_dashboard")

    existing_feedback = BookingFeedback.objects.filter(booking=booking, customer=request.user).first()

    if request.method == "POST":
        form = BookingFeedbackForm(request.POST, instance=existing_feedback)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.booking = booking
            feedback.customer = request.user
            feedback.save()
            messages.success(request, "Feedback submitted successfully.")
            return redirect("user_dashboard")
    else:
        form = BookingFeedbackForm(instance=existing_feedback)

    return render(
        request,
        "bookings/booking_feedback.html",
        {
            "booking": booking,
            "form": form,
            "existing_feedback": existing_feedback,
        },
    )


@role_required(CustomUser.Roles.CUSTOMER)
@require_POST
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.customer_id != request.user.id:
        messages.error(request, "You can only cancel your own bookings.")
        return redirect("user_dashboard")
    if booking.status != Booking.Status.PENDING:
        messages.error(request, "Only pending bookings can be cancelled.")
        return redirect("user_dashboard")

    booking.status = Booking.Status.CANCELLED
    booking.save(update_fields=["status"])

    target = _dashboard_name_for(request.user)
    messages.info(request, "Booking cancelled.")
    return redirect(target)


@role_required(CustomUser.Roles.STAFF, CustomUser.Roles.ADMIN)
@never_cache
def analytics(request):
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if request.user.role == CustomUser.Roles.STAFF:
        base = Booking.objects.filter(staff=request.user)
    else:
        base = Booking.objects.all()

    total_bookings = base.count()
    this_month = base.filter(created_at__gte=month_start).count()

    status_breakdown = {
        key: base.filter(status=key).count() for key, _ in Booking.Status.choices
    }

    popular_services_qs = (
        base.values("service__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:6]
    )

    if request.user.role == CustomUser.Roles.STAFF:
        staff_rows = [
            {
                "staff_name": request.user.display_name,
                "total": total_bookings,
                "completed": base.filter(status=Booking.Status.COMPLETED).count(),
            }
        ]
    else:
        staff_rows = []
        for staff_user in CustomUser.objects.filter(role=CustomUser.Roles.STAFF).order_by("first_name", "last_name", "username"):
            staff_base = base.filter(staff=staff_user)
            staff_rows.append(
                {
                    "staff_name": staff_user.display_name,
                    "total": staff_base.count(),
                    "completed": staff_base.filter(status=Booking.Status.COMPLETED).count(),
                }
            )
        staff_rows.sort(key=lambda row: (row["completed"], row["total"]), reverse=True)

    context = {
        "total_bookings": total_bookings,
        "this_month": this_month,
        "status_breakdown": status_breakdown,
        "popular_service_labels": [row["service__name"] for row in popular_services_qs],
        "popular_service_data": [row["total"] for row in popular_services_qs],
        "staff_rows": staff_rows,
    }
    return render(request, "bookings/analytics.html", context)


@login_required
@never_cache
def profile(request):
    if request.method == "POST":
        profile_action = request.POST.get("profile_action")
        if profile_action == "photo":
            profile_user = request.user
            remove_avatar = request.POST.get("remove_avatar") == "1"
            uploaded_avatar = request.FILES.get("avatar")

            if uploaded_avatar:
                profile_user.avatar = uploaded_avatar
                profile_user.save(update_fields=["avatar"])
                messages.success(request, "Profile photo updated.")
                return redirect("profile")

            if remove_avatar and profile_user.avatar:
                profile_user.avatar.delete(save=False)
                profile_user.avatar = None
                profile_user.save(update_fields=["avatar"])
                messages.success(request, "Profile photo removed.")
                return redirect("profile")

            messages.warning(request, "Please choose a photo to upload.")
            return redirect("profile")

        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            profile_user = form.save(commit=False)
            profile_user.save()
            messages.success(request, "Profile details updated.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)

    return render(request, "bookings/profile.html", {"form": form})
