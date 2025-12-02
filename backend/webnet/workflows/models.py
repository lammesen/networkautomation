from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class Workflow(models.Model):
    """Versioned workflow definition composed of nodes and edges."""

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="workflows"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(blank=True, null=True)
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflows_created",
    )
    updated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflows_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - display helper
        return self.name

    def bump_version(self) -> None:
        self.version += 1
        self.save(update_fields=["version", "updated_at"])


class WorkflowNode(models.Model):
    """A single node within a workflow graph."""

    CATEGORY_CHOICES = (
        ("service", "Service"),
        ("logic", "Logic"),
        ("data", "Data"),
        ("notification", "Notification"),
    )

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="nodes")
    ref = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    type = models.CharField(max_length=64)
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)
    order_index = models.PositiveIntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)
    ui_state = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ["order_index", "id"]
        indexes = [
            models.Index(fields=["workflow"]),
            models.Index(fields=["category"]),
            models.Index(fields=["type"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.name} ({self.type})"


class WorkflowEdge(models.Model):
    """Directed edge connecting workflow nodes."""

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="edges")
    source = models.ForeignKey(
        WorkflowNode, on_delete=models.CASCADE, related_name="outgoing_edges"
    )
    target = models.ForeignKey(
        WorkflowNode, on_delete=models.CASCADE, related_name="incoming_edges"
    )
    condition = models.CharField(
        max_length=512,
        blank=True,
        help_text="Python-like expression evaluated against context/outputs to traverse edge",
    )
    label = models.CharField(max_length=128, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["workflow"]),
            models.Index(fields=["source"]),
            models.Index(fields=["target"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.source_id} -> {self.target_id}"


class WorkflowRun(models.Model):
    """Execution record for a workflow version."""

    STATUS_CHOICES = (
        ("queued", "Queued"),
        ("running", "Running"),
        ("success", "Success"),
        ("partial", "Partial"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    )

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="runs")
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="workflow_runs"
    )
    started_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_runs",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    inputs = models.JSONField(blank=True, null=True)
    outputs = models.JSONField(blank=True, null=True)
    summary = models.JSONField(blank=True, null=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workflow"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"WorkflowRun {self.id} ({self.workflow_id})"

    def mark_started(self) -> None:
        self.status = "running"
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_finished(self, status: str, outputs: dict | None = None) -> None:
        self.status = status
        self.finished_at = timezone.now()
        if outputs is not None:
            self.outputs = outputs
        self.save(update_fields=["status", "finished_at", "outputs"])


class WorkflowRunStep(models.Model):
    """Execution status for a single node within a run."""

    STATUS_CHOICES = (
        ("queued", "Queued"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    )

    run = models.ForeignKey(WorkflowRun, on_delete=models.CASCADE, related_name="steps")
    node = models.ForeignKey(WorkflowNode, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    output = models.JSONField(blank=True, null=True)
    error = models.TextField(blank=True)
    transition = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["run"]),
            models.Index(fields=["node"]),
            models.Index(fields=["status"]),
        ]


class WorkflowRunLog(models.Model):
    """Lightweight log stream for workflow runs."""

    LEVEL_CHOICES = (
        ("DEBUG", "DEBUG"),
        ("INFO", "INFO"),
        ("WARN", "WARN"),
        ("ERROR", "ERROR"),
    )

    run = models.ForeignKey(WorkflowRun, on_delete=models.CASCADE, related_name="logs")
    node = models.ForeignKey(WorkflowNode, on_delete=models.SET_NULL, null=True, blank=True)
    ts = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="INFO")
    message = models.TextField()
    context = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ["ts"]
        indexes = [
            models.Index(fields=["run", "ts"]),
            models.Index(fields=["level"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.level}: {self.message}"
