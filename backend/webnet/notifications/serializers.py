"""Serializers for notifications API."""

from rest_framework import serializers
from webnet.notifications.models import SMTPConfig, NotificationPreference, NotificationEvent


class SMTPConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMTPConfig
        fields = [
            "id",
            "customer",
            "host",
            "port",
            "use_tls",
            "use_ssl",
            "username",
            "password",
            "from_email",
            "reply_to_email",
            "enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def to_representation(self, instance):
        """Mask password in responses."""
        data = super().to_representation(instance)
        if instance._password:
            data["password"] = "********"
        else:
            data["password"] = None
        return data


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "user",
            "customer",
            "event_type",
            "event_type_display",
            "enabled",
            "email_address",
            "job_types",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class NotificationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationEvent
        fields = [
            "id",
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
        read_only_fields = [
            "id",
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
