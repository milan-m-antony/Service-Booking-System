from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("professional-staff/", views.professional_staff, name="professional_staff"),
    path("messages/", views.message_center, name="messages"),
    path("login/", views.login_view, name="login"),
    path("force-password-change/", views.force_password_change, name="force_password_change"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("search/", views.global_search, name="global_search"),
    path("dashboard/", views.role_dashboard, name="role_dashboard"),
    path("dashboard/user/", views.user_dashboard, name="user_dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/admin/categories/", views.admin_categories, name="admin_categories"),
    path("dashboard/admin/categories/edit/<int:category_id>/", views.admin_edit_category, name="admin_edit_category"),
    path("dashboard/admin/services/", views.admin_services, name="admin_services"),
    path("dashboard/admin/services/edit/<int:service_id>/", views.admin_edit_service, name="admin_edit_service"),
    path("dashboard/admin/staff/", views.admin_staff, name="admin_staff"),
    path("dashboard/admin/users/", views.admin_users, name="admin_users"),
    path("bookings/create/", views.booking_create, name="booking_create"),
    path("dashboard/staff/", views.staff_dashboard, name="staff_dashboard"),
    path("dashboard/staff/availability/", views.staff_availability, name="staff_availability"),
    path("dashboard/analytics/", views.analytics, name="analytics"),
    path("bookings/<int:booking_id>/status/", views.update_booking_status, name="update_booking_status"),
    path("bookings/<int:booking_id>/feedback/", views.booking_feedback, name="booking_feedback"),
    path("bookings/<int:booking_id>/cancel/", views.cancel_booking, name="cancel_booking"),
    path("profile/", views.profile, name="profile"),
    path("filter-services/", views.filter_services, name="filter_services"),
]
