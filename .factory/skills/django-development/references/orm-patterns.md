ORM quick patterns (token-light)
================================
- Always scope by customer_id; avoid raw SQL; prefer QuerySet methods.
- Fetching: use select_related for FK/OneToOne; prefetch_related for reverse/M2M; slice/paginate large lists.
- Aggregations: annotate Count/Sum/Avg, use Q for conditional counts; F expressions for in-place updates.
- Consistency: wrap multi-step writes in transaction.atomic(); use update() for bulk changes, avoid Python loops.
- Indexing: add db_index on customer/date/status when filtered; use unique_together on (customer, <field>) as needed.
- Time: timezone.now(), auto_now_add/auto_now; avoid naive datetimes.
