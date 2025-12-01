---
name: ai-data-analyst
description: Use for analyzing webnet operational data (jobs/devices/compliance) with Python (pandas/matplotlib) and Django ORM.
license: MIT
---

# AI Data Analyst (webnet)

Purpose: produce reproducible analyses and charts for jobs, devices, compliance, or topology using local data.

Rules
- ALWAYS run sequentialThinking before analysis.
- Keep data read-only and tenant-safe; never expose secrets/PII.

When to use
- Job performance/failure analysis
- Device inventory trends
- Compliance status over time
- Stakeholder reports with charts/tables

Inputs
- Questions/metrics, time range, customer scope, output format (tables/charts/report).

Setup (minimal)
```python
import os, sys, django
sys.path.insert(0, '/Users/mlt/Documents/Github/networkautomation/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webnet.settings')
django.setup()
```
Then import pandas/matplotlib/seaborn and relevant models (Device, Job, JobLog, ConfigSnapshot, ComplianceResult, Customer, User).

Process
1) Define goals and scope (customers/time window).
2) Pull data via Django ORM; convert to DataFrame.
3) Compute metrics (rates, counts, trends) and visualize.
4) Save outputs (PNG/CSV/Markdown) in repo-safe location.
5) Summarize findings with caveats.

Required artifacts
- Script/notebook with Django setup and queries
- Saved charts/tables
- Written summary (assumptions, limitations)

Checklist
- Queries scoped by customer/time
- No credentials/PII in outputs
- Scripts rerunnable; dependencies noted

Verification
- Run script via venv python; confirm outputs in target directory.

Resources: `docs/models-reference.md` for fields; reuse patterns from `webnet/jobs` and `webnet/devices` models.
