from django.conf import settings
from django.shortcuts import redirect


class RequireLoginMiddleware:
    """Redirect unauthenticated users to LOGIN_URL except for exempt prefixes."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_prefixes = tuple(getattr(settings, "LOGIN_EXEMPT_PREFIXES", ()))

    def __call__(self, request):
        path = request.path
        if path.startswith(self.exempt_prefixes) or request.user.is_authenticated:
            return self.get_response(request)
        return redirect(f"{settings.LOGIN_URL}?next={request.get_full_path()}")
