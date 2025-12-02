"""Custom fields infrastructure for webnet.

This module provides support for user-defined custom fields on models,
allowing organizations to store custom data without modifying models.
"""

from django.db import models
from typing import Any
import json


class CustomFieldDefinition(models.Model):
    """Definition of a custom field that can be added to models.

    Custom fields are defined per model type and can have various data types
    with validation rules. The actual values are stored in JSONField on the models.
    """

    TYPE_TEXT = "text"
    TYPE_TEXTAREA = "textarea"
    TYPE_INTEGER = "integer"
    TYPE_DECIMAL = "decimal"
    TYPE_BOOLEAN = "boolean"
    TYPE_DATE = "date"
    TYPE_DATETIME = "datetime"
    TYPE_URL = "url"
    TYPE_JSON = "json"
    TYPE_SELECT = "select"
    TYPE_MULTISELECT = "multiselect"

    TYPE_CHOICES = [
        (TYPE_TEXT, "Text (Single Line)"),
        (TYPE_TEXTAREA, "Text (Multi-Line)"),
        (TYPE_INTEGER, "Integer"),
        (TYPE_DECIMAL, "Decimal"),
        (TYPE_BOOLEAN, "Boolean"),
        (TYPE_DATE, "Date"),
        (TYPE_DATETIME, "Date & Time"),
        (TYPE_URL, "URL"),
        (TYPE_JSON, "JSON"),
        (TYPE_SELECT, "Selection (Dropdown)"),
        (TYPE_MULTISELECT, "Multi-Select"),
    ]

    # Models that support custom fields
    MODEL_DEVICE = "device"
    MODEL_CREDENTIAL = "credential"
    MODEL_JOB = "job"
    MODEL_COMPLIANCE_POLICY = "compliancepolicy"
    MODEL_CONFIG_SNAPSHOT = "configsnapshot"
    MODEL_CONFIG_TEMPLATE = "configtemplate"
    MODEL_TAG = "tag"
    MODEL_DEVICE_GROUP = "devicegroup"

    MODEL_CHOICES = [
        (MODEL_DEVICE, "Device"),
        (MODEL_CREDENTIAL, "Credential"),
        (MODEL_JOB, "Job"),
        (MODEL_COMPLIANCE_POLICY, "Compliance Policy"),
        (MODEL_CONFIG_SNAPSHOT, "Config Snapshot"),
        (MODEL_CONFIG_TEMPLATE, "Config Template"),
        (MODEL_TAG, "Tag"),
        (MODEL_DEVICE_GROUP, "Device Group"),
    ]

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="custom_field_definitions",
        help_text="Customer this custom field belongs to",
    )
    name = models.CharField(
        max_length=100,
        help_text="Internal name (used in API, must be unique per model)",
    )
    label = models.CharField(
        max_length=100,
        help_text="Display label for the field",
    )
    model_type = models.CharField(
        max_length=50,
        choices=MODEL_CHOICES,
        help_text="Which model this field applies to",
    )
    field_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_TEXT,
        help_text="Data type for this field",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description or help text for this field",
    )
    required = models.BooleanField(
        default=False,
        help_text="Whether this field is required",
    )
    default_value = models.TextField(
        blank=True,
        null=True,
        help_text="Default value (as string, will be converted to field type)",
    )
    choices = models.JSONField(
        blank=True,
        null=True,
        help_text="For select/multiselect: list of valid choices",
    )
    validation_regex = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Optional regex pattern for text validation",
    )
    validation_min = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Minimum value for integer/decimal fields",
    )
    validation_max = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Maximum value for integer/decimal fields",
    )
    weight = models.IntegerField(
        default=100,
        help_text="Display order (lower numbers appear first)",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this field is currently active",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("customer", "model_type", "name")
        ordering = ["model_type", "weight", "name"]
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["model_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.label} ({self.model_type})"

    def validate_value(self, value: Any) -> tuple[bool, str | None]:
        """Validate a value against this field's definition.

        Args:
            value: The value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Required field check
        if self.required and (value is None or value == ""):
            return False, f"{self.label} is required"

        # Allow None/empty for optional fields
        if value is None or value == "":
            return True, None

        # Type-specific validation
        try:
            if self.field_type == self.TYPE_INTEGER:
                val = int(value)
                if self.validation_min is not None and val < self.validation_min:
                    return False, f"{self.label} must be >= {self.validation_min}"
                if self.validation_max is not None and val > self.validation_max:
                    return False, f"{self.label} must be <= {self.validation_max}"

            elif self.field_type == self.TYPE_DECIMAL:
                val = float(value)
                if self.validation_min is not None and val < float(self.validation_min):
                    return False, f"{self.label} must be >= {self.validation_min}"
                if self.validation_max is not None and val > float(self.validation_max):
                    return False, f"{self.label} must be <= {self.validation_max}"

            elif self.field_type == self.TYPE_BOOLEAN:
                if not isinstance(value, bool):
                    if str(value).lower() not in ["true", "false", "1", "0"]:
                        return False, f"{self.label} must be true or false"

            elif self.field_type == self.TYPE_DATE:
                from datetime import datetime

                if isinstance(value, str):
                    datetime.fromisoformat(value.replace("Z", "+00:00"))

            elif self.field_type == self.TYPE_DATETIME:
                from datetime import datetime

                if isinstance(value, str):
                    datetime.fromisoformat(value.replace("Z", "+00:00"))

            elif self.field_type == self.TYPE_URL:
                from django.core.validators import URLValidator

                validator = URLValidator()
                validator(str(value))

            elif self.field_type == self.TYPE_JSON:
                if isinstance(value, str):
                    json.loads(value)

            elif self.field_type == self.TYPE_SELECT:
                if self.choices and value not in self.choices:
                    return False, f"{self.label} must be one of: {', '.join(self.choices)}"

            elif self.field_type == self.TYPE_MULTISELECT:
                if self.choices:
                    if not isinstance(value, list):
                        return False, f"{self.label} must be a list"
                    for v in value:
                        if v not in self.choices:
                            return False, f"Invalid choice: {v}"

            elif self.field_type in [self.TYPE_TEXT, self.TYPE_TEXTAREA]:
                if self.validation_regex:
                    import re

                    if not re.match(self.validation_regex, str(value)):
                        return False, f"{self.label} does not match required pattern"

        except (ValueError, TypeError) as e:
            return False, f"{self.label} has invalid value: {str(e)}"

        return True, None

    def get_default(self) -> Any:
        """Get the default value for this field, converted to the appropriate type."""
        if not self.default_value:
            return None

        try:
            if self.field_type == self.TYPE_INTEGER:
                return int(self.default_value)
            elif self.field_type == self.TYPE_DECIMAL:
                return float(self.default_value)
            elif self.field_type == self.TYPE_BOOLEAN:
                return self.default_value.lower() in ["true", "1"]
            elif self.field_type == self.TYPE_JSON:
                return json.loads(self.default_value)
            elif self.field_type == self.TYPE_MULTISELECT:
                return (
                    json.loads(self.default_value)
                    if isinstance(self.default_value, str)
                    else self.default_value
                )
            else:
                return self.default_value
        except (ValueError, json.JSONDecodeError):
            return None


class CustomFieldMixin(models.Model):
    """Mixin to add custom fields support to any model.

    Models using this mixin will have a `custom_fields` JSONField
    for storing custom field values.
    """

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom field values stored as JSON",
    )

    class Meta:
        abstract = True

    def validate_custom_fields(self, customer_id: int, model_type: str) -> tuple[bool, list[str]]:
        """Validate custom field values against their definitions.

        Args:
            customer_id: Customer ID to look up field definitions
            model_type: Model type (e.g., 'device', 'job')

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Get active field definitions for this model type
        definitions = CustomFieldDefinition.objects.filter(
            customer_id=customer_id,
            model_type=model_type,
            is_active=True,
        )

        # Validate each field
        for field_def in definitions:
            value = self.custom_fields.get(field_def.name)
            is_valid, error = field_def.validate_value(value)
            if not is_valid:
                errors.append(error)

        return len(errors) == 0, errors

    def get_custom_field_value(self, field_name: str) -> Any:
        """Get a custom field value by name."""
        return self.custom_fields.get(field_name)

    def set_custom_field_value(self, field_name: str, value: Any) -> None:
        """Set a custom field value by name."""
        if self.custom_fields is None:
            self.custom_fields = {}
        self.custom_fields[field_name] = value
