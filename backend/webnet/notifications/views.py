"""API views for notifications."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from webnet.api.permissions import RolePermission, ObjectCustomerPermission, CustomerScopedQuerysetMixin
from webnet.notifications.models import SMTPConfig, NotificationPreference, NotificationEvent
from webnet.notifications.serializers import (
    SMTPConfigSerializer,
    NotificationPreferenceSerializer,
    NotificationEventSerializer,
)
from webnet.notifications.services import EmailService


class SMTPConfigViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for SMTP configuration."""

    queryset = SMTPConfig.objects.all()
    serializer_class = SMTPConfigSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "customer_id"
    filterset_fields = ["customer", "enabled"]

    @action(detail=True, methods=["post"])
    def test_email(self, request, pk=None):
        """Send a test email to verify SMTP configuration."""
        smtp_config = self.get_object()
        
        # Get recipient email from request or use user's email
        recipient = request.data.get("recipient_email", request.user.email)
        
        if not recipient:
            return Response(
                {"error": "No recipient email address provided or found in user profile"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Send test email
        email_service = EmailService(smtp_config)
        success, error_msg = email_service.send_test_email(recipient)
        
        if success:
            return Response(
                {"message": f"Test email sent successfully to {recipient}"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": error_msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


class NotificationPreferenceViewSet(CustomerScopedQuerysetMixin, viewsets.ModelViewSet):
    """ViewSet for notification preferences."""

    queryset = NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "customer_id"
    filterset_fields = ["customer", "user", "event_type", "enabled"]

    def get_queryset(self):
        """Filter to current user's preferences unless admin."""
        qs = super().get_queryset()
        
        # Admins can see all preferences, others only their own
        if self.request.user.role != "admin":
            qs = qs.filter(user=self.request.user)
        
        return qs

    @action(detail=False, methods=["get"])
    def my_preferences(self, request):
        """Get current user's notification preferences."""
        prefs = NotificationPreference.objects.filter(
            user=request.user,
            customer__in=request.user.customers.all(),
        )
        serializer = self.get_serializer(prefs, many=True)
        return Response(serializer.data)


class NotificationEventViewSet(CustomerScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet for notification event logs (read-only)."""

    queryset = NotificationEvent.objects.all()
    serializer_class = NotificationEventSerializer
    permission_classes = [IsAuthenticated, RolePermission, ObjectCustomerPermission]
    customer_field = "customer_id"
    filterset_fields = ["customer", "event_type", "status", "job", "compliance_result"]
    ordering_fields = ["created_at", "sent_at"]
    ordering = ["-created_at"]
