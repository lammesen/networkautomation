name: ai-data-analyst
description: This skill should be used when the user asks to "analyze job performance", "visualize device trends", "chart compliance", or needs Python data analysis with matplotlib/pandas.
Analyze data with pandas/matplotlib. **Use sequentialThinking.**

Quick Django setup:
```python
import os, sys, django
sys.path.insert(0, 'backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webnet.settings')
django.setup()
```

Patterns: job success/error rates by day/type, job duration, device/vendor/site distribution, compliance pass rate. Save charts with `plt.savefig('analysis_output/name.png', dpi=300)`.

Output: script/notebook + PNGs + brief summary. Guardrails: read-only queries, respect customer scoping, never log secrets.
