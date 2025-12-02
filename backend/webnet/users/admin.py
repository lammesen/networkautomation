"""Admin configuration for users app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils.html import format_html

from webnet.users.models import User, APIKey
from webnet.users.two_factor_service import TwoFactorService


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin with 2FA management."""

    list_display = (
        "username",
        "email",
        "role",
        "is_2fa_enabled",
        "two_factor_required",
        "is_staff",
        "is_active",
    )
    list_filter = (
        "role",
        "two_factor_enabled",
        "two_factor_required",
        "is_staff",
        "is_active",
    )
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Role & Customers",
            {
                "fields": ("role", "customers"),
            },
        ),
        (
            "Two-Factor Authentication",
            {
                "fields": (
                    "two_factor_enabled",
                    "two_factor_required",
                    "backup_codes_count",
                ),
            },
        ),
    )
    readonly_fields = ("backup_codes_count",)
    filter_horizontal = ("customers",)

    def is_2fa_enabled(self, obj: User) -> bool:
        """Display if 2FA is enabled."""
        return obj.two_factor_enabled

    is_2fa_enabled.boolean = True  # type: ignore
    is_2fa_enabled.short_description = "2FA Enabled"  # type: ignore

    def backup_codes_count(self, obj: User) -> str:
        """Display count of backup codes."""
        count = len(obj.backup_codes) if obj.backup_codes else 0
        return f"{count} backup codes remaining"

    backup_codes_count.short_description = "Backup Codes"  # type: ignore

    def get_form(self, request, obj=None, **kwargs):
        """Add 2FA reset button to change form."""
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.two_factor_enabled:
            # Add help text with reset button
            help_text = format_html(
                'User has 2FA enabled. <a href="{}" class="button" '
                'onclick="return confirm(\'Are you sure you want to reset 2FA for this user?\');">'
                "Reset 2FA</a>",
                reverse("2fa-admin-reset", args=[obj.id]),
            )
            form.base_fields["two_factor_enabled"].help_text = help_text
        return form


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """Admin for API keys."""

    list_display = (
        "user",
        "name",
        "key_prefix",
        "is_active",
        "expires_at",
        "last_used_at",
        "created_at",
    )
    list_filter = ("is_active", "created_at", "expires_at")
    search_fields = ("user__username", "name", "key_prefix")
    readonly_fields = ("key_prefix", "key_hash", "created_at", "last_used_at")
    date_hierarchy = "created_at"

    fieldsets = (
        (
            None,
            {
                "fields": ("user", "name", "is_active"),
            },
        ),
        (
            "Key Information",
            {
                "fields": ("key_prefix", "key_hash"),
            },
        ),
        (
            "Scopes & Expiration",
            {
                "fields": ("scopes", "expires_at"),
            },
        ),
        (
            "Usage",
            {
                "fields": ("last_used_at", "created_at"),
            },
        ),
    )
