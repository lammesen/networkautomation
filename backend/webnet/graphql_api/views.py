"""GraphQL views for webnet."""

from strawberry.django.views import AsyncGraphQLView as BaseAsyncGraphQLView
from django.http import HttpResponseForbidden

from .auth import get_user_from_request


class GraphQLView(BaseAsyncGraphQLView):
    """GraphQL view with custom authentication support."""

    def dispatch(self, request, *args, **kwargs):
        """Require token/API key auth to avoid session-based CSRF exposure."""
        auth_header = request.headers.get("Authorization") or request.headers.get("X-API-Key")
        if not auth_header:
            return HttpResponseForbidden("Authorization header required")
        return super().dispatch(request, *args, **kwargs)

    def get_context(self, request, response=None):
        """Build context with authenticated user."""
        # Try to authenticate via JWT or API key
        user = get_user_from_request(request)
        if user:
            request.user = user

        return {
            "request": request,
            "response": response,
        }
