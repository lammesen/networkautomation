---
name: data-querying
description: Use for answering questions with Django ORM over webnet data (devices, jobs, configs, compliance).
license: MIT
---

# Internal Data Querying (webnet)

Purpose: craft reproducible, tenant-safe ORM queries for metrics/reports on devices, jobs, configs, compliance, or topology.

Rules
- ALWAYS run sequentialThinking before querying.
- Use Django ORM (no raw SQL) and scope by customer.

When to use
- Inventory metrics, job success rates, compliance counts/trends, error analysis, quick reports/commands.

Inputs
- Business question, time range/filters, target models, sensitivity constraints.

Key models/fields
- Device (vendor/platform/site/role/enabled/reachability_status)
- Job / JobLog (type/status/user/customer/timestamps/message/host)
- ConfigSnapshot (device, created_at, hash)
- CompliancePolicy / ComplianceResult (policy/device/status/ts)
- TopologyLink (local_device, remote_hostname)
- Customer, User

Patterns (snippets)
```python
from django.db.models import Count, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

# Jobs last 7d by status
since = timezone.now() - timedelta(days=7)
Job.objects.filter(requested_at__gte=since).values('status').annotate(count=Count('id'))

# Devices by vendor (scoped)
Device.objects.filter(customer_id=cust).values('vendor').annotate(count=Count('id')).order_by('-count')
```

Required behavior
- Customer scoping on every query unless admin use-case
- Exclude credential fields; avoid leaking IPs if not needed
- Document assumptions/filters; make commands rerunnable

Artifacts
- ORM code (shell snippet or management command)
- Result table/JSON and short summary

Verification
- Run in Django shell (`cd backend && ../backend/venv/bin/python manage.py shell`)
- Confirm outputs match expectations and scope

Resources: `docs/models-reference.md`, optional `references/query-patterns.md`.
