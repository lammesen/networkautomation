from __future__ import annotations

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("customers", "0002_customer_ssh_host_key_policy"),
        ("users", "0003_webauthn_credential"),
    ]

    operations = [
        migrations.CreateModel(
            name="Workflow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="workflows_created", to="users.user")),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="workflows", to="customers.customer")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="workflows_updated", to="users.user")),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("success", "Success"), ("partial", "Partial"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="queued", max_length=20)),
                ("inputs", models.JSONField(blank=True, null=True)),
                ("outputs", models.JSONField(blank=True, null=True)),
                ("summary", models.JSONField(blank=True, null=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="workflow_runs", to="customers.customer")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowNode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ref", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("category", models.CharField(choices=[("service", "Service"), ("logic", "Logic"), ("data", "Data"), ("notification", "Notification")], max_length=32)),
                ("type", models.CharField(max_length=64)),
                ("position_x", models.FloatField(default=0)),
                ("position_y", models.FloatField(default=0)),
                ("order_index", models.PositiveIntegerField(default=0)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("ui_state", models.JSONField(blank=True, null=True)),
                ("workflow", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="nodes", to="workflows.workflow")),
            ],
            options={
                "ordering": ["order_index", "id"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowRunStep",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("success", "Success"), ("failed", "Failed"), ("skipped", "Skipped")], default="queued", max_length=20)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("output", models.JSONField(blank=True, null=True)),
                ("error", models.TextField(blank=True)),
                ("transition", models.CharField(blank=True, max_length=128)),
                ("node", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="workflows.workflownode")),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="steps", to="workflows.workflowrun")),
            ],
            options={
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowRunLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ts", models.DateTimeField(auto_now_add=True)),
                ("level", models.CharField(choices=[("DEBUG", "DEBUG"), ("INFO", "INFO"), ("WARN", "WARN"), ("ERROR", "ERROR")], default="INFO", max_length=10)),
                ("message", models.TextField()),
                ("context", models.JSONField(blank=True, null=True)),
                ("node", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="workflows.workflownode")),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="logs", to="workflows.workflowrun")),
            ],
            options={
                "ordering": ["ts"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowEdge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("condition", models.CharField(blank=True, help_text="Python-like expression evaluated against context/outputs to traverse edge", max_length=512)),
                ("label", models.CharField(blank=True, max_length=128)),
                ("is_default", models.BooleanField(default=False)),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outgoing_edges", to="workflows.workflownode")),
                ("target", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="incoming_edges", to="workflows.workflownode")),
                ("workflow", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="edges", to="workflows.workflow")),
            ],
        ),
        migrations.AddField(
            model_name="workflowrun",
            name="workflow",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="runs", to="workflows.workflow"),
        ),
        migrations.AddField(
            model_name="workflowrun",
            name="started_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="workflow_runs", to="users.user"),
        ),
        migrations.AddIndex(
            model_name="workflowrun",
            index=models.Index(fields=["workflow"], name="workflows_w_workflo_0e34d3_idx"),
        ),
        migrations.AddIndex(
            model_name="workflowrun",
            index=models.Index(fields=["customer"], name="workflows_w_customer_348ad2_idx"),
        ),
        migrations.AddIndex(
            model_name="workflowrun",
            index=models.Index(fields=["status"], name="workflows_w_status_3635d5_idx"),
        ),
        migrations.AddIndex(
            model_name="workflowedge",
            index=models.Index(fields=["workflow"], name="workflows_w_workflo_8af680_idx"),
        ),
        migrations.AddIndex(
            model_name="workflowedge",
            index=models.Index(fields=["source"], name="workflows_w_source_3f6fd5_idx"),
        ),
        migrations.AddIndex(
            model_name="workflowedge",
            index=models.Index(fields=["target"], name="workflows_w_target_778cdb_idx"),
        ),
        migrations.AddIndex(
            model_name="workflownode",
            index=models.Index(fields=["workflow"], name="workflows_w_workflo_0c43c4_idx"),
        ),
        migrations.AddIndex(
            model_name="workflownode",
            index=models.Index(fields=["category"], name="workflows_w_categor_b33ae4_idx"),
        ),
        migrations.AddIndex(
            model_name="workflownode",
            index=models.Index(fields=["type"], name="workflows_w_type_12f83b_idx"),
        ),
        migrations.AddIndex(
            model_name="workflowrunstep",
            index=models.Index(fields=["run"], name="workflows_w_run_id_4dcbcf_idx"),
        ),
        migrations.AddIndex(
            model_name="workflowrunstep",
            index=models.Index(fields=["node"], name="workflows_w_node_id_a96c27_idx"),
        ),
        migrations.AddIndex(
            model_name="workflowrunstep",
            index=models.Index(fields=["status"], name="workflows_w_status_8685af_idx"),
        ),
        migrations.AddIndex(
            model_name="workflowrunlog",
            index=models.Index(fields=["run", "ts"], name="workflows_w_run_id_2d561f_idx"),
        ),
        migrations.AddIndex(
            model_name="workflowrunlog",
            index=models.Index(fields=["level"], name="workflows_w_level_8743b9_idx"),
        ),
        migrations.AddIndex(
            model_name="workflow",
            index=models.Index(fields=["customer"], name="workflows_w_customer_7fdf98_idx"),
        ),
        migrations.AddIndex(
            model_name="workflow",
            index=models.Index(fields=["is_active"], name="workflows_w_is_act_c3fc70_idx"),
        ),
    ]
