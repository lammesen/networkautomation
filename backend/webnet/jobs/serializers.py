"""Internal serializers for job artifacts."""

from rest_framework import serializers
from webnet.jobs.models import JobLog


class JobLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobLog
        fields = ["id", "job", "ts", "level", "host", "message", "extra_json"]
