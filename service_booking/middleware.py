from django.db.utils import DatabaseError, OperationalError, NotSupportedError
from django.shortcuts import render


class DatabaseErrorMiddleware:
    """Catch DB connection/version errors and render a friendly 503 page.

    This prevents internal server errors caused by unsupported database
    versions (for example older MariaDB) from surfacing as raw 500 pages
    to end users.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except (DatabaseError, OperationalError, NotSupportedError) as exc:
            # Render a simple explanatory page with HTTP 503 Service Unavailable.
            context = {"error_message": str(exc)}
            return render(request, "db_unavailable.html", context, status=503)
