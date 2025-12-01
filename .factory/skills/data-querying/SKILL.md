name: data-querying
description: This skill should be used when the user asks to "query devices", "get job statistics", "report on compliance", or needs Django ORM queries for metrics and reports.
Query webnet data with Django ORM. **Use sequentialThinking.**

Key models: Device(hostname, mgmt_ip, vendor, site, customer_id, enabled); Job(type, status, requested_at/finished_at, customer_id); JobLog(job, level, host, message); ConfigSnapshot(device, created_at, hash); ComplianceResult(policy, device, status, ts).

Common snippets:
```python
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
Device.objects.filter(customer_id=cid, enabled=True).values('vendor').annotate(count=Count('id'))
since = timezone.now() - timedelta(days=7)
Job.objects.filter(customer_id=cid, requested_at__gte=since).values('status').annotate(count=Count('id'))
Job.objects.filter(customer_id=cid).values('type').annotate(total=Count('id'), success=Count('id', filter=Q(status='success')))
JobLog.objects.filter(job__customer_id=cid, level='ERROR').values('message').annotate(count=Count('id'))[:10]
```

Guardrails: always scope by customer, use ORM (no raw SQL), avoid secret fields.
