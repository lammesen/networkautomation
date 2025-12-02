"""Django admin configuration for core models."""

from django.contrib import admin
from webnet.core.models import CustomFieldDefinition


@admin.register(CustomFieldDefinition)
class CustomFieldDefinitionAdmin(admin.ModelAdmin):
    """Admin interface for CustomFieldDefinition."""

    list_display = [
        "name",
        "label",
        "model_type",
        "field_type",
        "customer",
        "required",
        "is_active",
    ]
    list_filter = ["model_type", "field_type", "required", "is_active", "customer"]
    search_fields = ["name", "label", "description"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "customer",
                    "name",
                    "label",
                    "model_type",
                    "field_type",
                    "description",
                )
            },
        ),
        (
            "Validation",
            {
                "fields": (
                    "required",
                    "default_value",
                    "choices",
                    "validation_regex",
                    "validation_min",
                    "validation_max",
                )
            },
        ),
        (
            "Display Options",
            {"fields": ("weight", "is_active")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at")},
        ),
    )
