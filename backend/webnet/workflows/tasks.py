from __future__ import annotations

from celery import shared_task

from webnet.workflows.executor import WorkflowExecutor
from webnet.workflows.models import WorkflowRun


@shared_task(name="workflows.execute")
def execute_workflow_run(run_id: int) -> dict | None:
    try:
        run = WorkflowRun.objects.select_related("workflow", "customer", "started_by").get(
            pk=run_id
        )
    except WorkflowRun.DoesNotExist:  # pragma: no cover - defensive guard
        return None

    executor = WorkflowExecutor(run)
    executor.execute()
    return {"run_id": run.id, "status": run.status}
