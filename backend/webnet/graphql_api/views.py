"""GraphQL views for webnet."""

from strawberry.django.views import AsyncGraphQLView as BaseAsyncGraphQLView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .auth import get_user_from_request


@method_decorator(csrf_exempt, name="dispatch")
class GraphQLView(BaseAsyncGraphQLView):
    """GraphQL view with custom authentication support."""

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
