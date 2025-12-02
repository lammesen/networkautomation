"""Django admin for notifications."""

from django.contrib import admin
from webnet.notifications.models import SMTPConfig, NotificationPreference, NotificationEvent


@admin.register(SMTPConfig)
class SMTPConfigAdmin(admin.ModelAdmin):
    list_display = ["customer", "host", "port", "from_email", "enabled", "created_at"]
    list_filter = ["enabled", "use_tls", "use_ssl"]
    search_fields = ["customer__name", "host", "from_email"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("customer", "enabled")}),
        ("SMTP Server", {"fields": ("host", "port", "use_tls", "use_ssl")}),
        ("Authentication", {"fields": ("username", "password")}),
        ("Email Addresses", {"fields": ("from_email", "reply_to_email")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "customer", "event_type", "enabled", "email_address", "created_at"]
    list_filter = ["enabled", "event_type", "customer"]
    search_fields = ["user__username", "customer__name", "email_address"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("user", "customer", "event_type", "enabled")}),
        ("Settings", {"fields": ("email_address", "job_types")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ["recipient_email", "event_type", "subject", "status", "sent_at", "created_at"]
    list_filter = ["status", "event_type", "created_at"]
    search_fields = ["recipient_email", "subject"]
    readonly_fields = [
        "customer",
        "recipient_email",
        "event_type",
        "subject",
        "status",
        "error_message",
        "job",
        "compliance_result",
        "sent_at",
        "created_at",
    ]

    def has_add_permission(self, request):
        """Notification events cannot be manually created."""
        return False

    def has_change_permission(self, request, obj=None):
        """Notification events cannot be changed."""
        return False
