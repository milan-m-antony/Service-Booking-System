from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if request.user.must_change_password:
                current_name = request.resolver_match.url_name if request.resolver_match else ""
                if current_name not in {"force_password_change", "logout"}:
                    messages.info(request, "Please update your temporary password first.")
                    return redirect("force_password_change")
            if request.user.role in allowed_roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            messages.error(request, "You do not have permission to access that page.")
            return redirect("home")

        return _wrapped_view

    return decorator
