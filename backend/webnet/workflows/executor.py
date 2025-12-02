from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any

from django.db import transaction
from django.utils import timezone

from webnet.jobs.services import JobService
from webnet.workflows.models import (
    WorkflowEdge,
    WorkflowNode,
    WorkflowRun,
    WorkflowRunLog,
    WorkflowRunStep,
)

logger = logging.getLogger(__name__)


class WorkflowExecutionError(Exception):
    """Raised when a workflow node fails execution."""


def _safe_eval(expr: str, *, context: dict[str, Any], last_output: dict[str, Any]) -> Any:
    """Evaluate simple expressions against a restricted context."""
    allowed_builtins = {"len": len, "min": min, "max": max, "sum": sum, "any": any, "all": all}
    scope = {"context": context, "last": last_output}
    try:
        return eval(expr, {"__builtins__": allowed_builtins}, scope)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Workflow condition eval failed: %s", exc)
        raise WorkflowExecutionError(f"Failed to evaluate condition: {exc}") from exc


class WorkflowExecutor:
    """Executes a workflow run in topological order with conditional edges."""

    def __init__(self, run: WorkflowRun):
        self.run = run
        self.context: dict[str, Any] = dict(run.inputs or {})
        self.outputs: dict[str, Any] = {}
        self.job_service = JobService()

    def _log(self, level: str, message: str, node: WorkflowNode | None = None, extra=None) -> None:
        WorkflowRunLog.objects.create(
            run=self.run,
            node=node,
            level=level,
            message=message,
            context=extra,
        )

    def _record_step_status(
        self,
        step: WorkflowRunStep,
        status: str,
        *,
        output: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        step.status = status
        if status == "running":
            step.started_at = timezone.now()
        if status in {"success", "failed", "skipped"}:
            step.finished_at = timezone.now()
        if output is not None:
            step.output = output
        if error is not None:
            step.error = error
        step.save(
            update_fields=[
                "status",
                "started_at",
                "finished_at",
                "output",
                "error",
                "transition",
            ]
        )

    def _execute_service_node(self, node: WorkflowNode) -> dict[str, Any]:
        job_type = node.config.get("job_type") or node.type
        target_summary = node.config.get("targets") or node.config.get("filters")
        payload = node.config.get("payload")
        simulate = bool(node.config.get("simulate", True))

        if not job_type:
            raise WorkflowExecutionError("job_type is required for service nodes")

        if simulate:
            self._log(
                "INFO",
                f"Simulated service node {job_type}",
                node=node,
                extra={"targets": target_summary},
            )
            return {"job_type": job_type, "simulated": True, "targets": target_summary}

        user = self.run.started_by or node.workflow.created_by
        job = self.job_service.create_job(
            job_type=job_type,
            user=user,
            customer=self.run.customer,
            target_summary=target_summary,
            payload=payload,
        )
        self._log("INFO", f"Queued job {job.id} for {job_type}", node=node)
        return {"job_id": job.id, "job_type": job.type, "targets": target_summary}

    def _execute_logic_node(self, node: WorkflowNode) -> dict[str, Any]:
        if node.type in {"if", "condition"}:
            expr = node.config.get("condition")
            if not expr:
                raise WorkflowExecutionError("condition is required for logic nodes")
            outcome = bool(_safe_eval(expr, context=self.context, last_output={}))
            return {"condition": outcome}

        if node.type == "switch":
            expr = node.config.get("expression")
            if not expr:
                raise WorkflowExecutionError("expression is required for switch nodes")
            value = _safe_eval(expr, context=self.context, last_output={})
            return {"value": value}

        if node.type == "loop":
            iterations = int(node.config.get("iterations", 1))
            return {"iterations": iterations}

        raise WorkflowExecutionError(f"Unsupported logic node type {node.type}")

    def _execute_data_node(self, node: WorkflowNode) -> dict[str, Any]:
        if node.type == "set_variable":
            key = node.config.get("key")
            value = node.config.get("value")
            if not key:
                raise WorkflowExecutionError("key is required for set_variable nodes")
            self.context[str(key)] = value
            return {"context": {key: value}}

        if node.type == "transform":
            expr = node.config.get("expression")
            if not expr:
                raise WorkflowExecutionError("expression is required for transform nodes")
            result = _safe_eval(expr, context=self.context, last_output={})
            return {"value": result}

        if node.type == "input":
            # Passthrough initial inputs to context
            return {"context": self.context}

        raise WorkflowExecutionError(f"Unsupported data node type {node.type}")

    def _execute_notification_node(self, node: WorkflowNode) -> dict[str, Any]:
        message = node.config.get("message") or "Notification"
        channel = node.config.get("channel") or "log"
        self._log("INFO", f"[notify:{channel}] {message}", node=node)
        return {"delivered": True, "channel": channel}

    def _execute_node(self, node: WorkflowNode) -> dict[str, Any]:
        if node.category == "service":
            return self._execute_service_node(node)
        if node.category == "logic":
            return self._execute_logic_node(node)
        if node.category == "data":
            return self._execute_data_node(node)
        if node.category == "notification":
            return self._execute_notification_node(node)
        raise WorkflowExecutionError(f"Unknown node category {node.category}")

    def _should_traverse(self, edge: WorkflowEdge, last_output: dict[str, Any]) -> bool:
        if edge.condition:
            result = _safe_eval(edge.condition, context=self.context, last_output=last_output)
            return bool(result)

        # For boolean-producing nodes, edge labels can map to True/False
        if "condition" in last_output:
            if edge.label:
                return str(edge.label).lower() == str(bool(last_output["condition"])).lower()
            return bool(last_output["condition"])

        return True

    def _mark_unvisited_steps(self, steps: dict[str, WorkflowRunStep]) -> None:
        for step in steps.values():
            if step.status == "queued":
                self._record_step_status(step, "skipped")
                self._log("WARN", f"Node {step.node_id} skipped (no incoming path)", node=step.node)

    @transaction.atomic
    def execute(self) -> WorkflowRun:
        self._log("INFO", f"Starting workflow run for {self.run.workflow.name}")
        self.run.mark_started()

        nodes = {str(node.ref): node for node in self.run.workflow.nodes.all()}
        edges_by_source: dict[str, list[WorkflowEdge]] = defaultdict(list)
        indegree: dict[str, int] = {ref: 0 for ref in nodes}

        for edge in self.run.workflow.edges.select_related("source", "target"):
            source_ref = str(edge.source.ref)
            target_ref = str(edge.target.ref)
            edges_by_source[source_ref].append(edge)
            indegree[target_ref] = indegree.get(target_ref, 0) + 1

        steps: dict[str, WorkflowRunStep] = {
            ref: WorkflowRunStep.objects.create(run=self.run, node=node)
            for ref, node in nodes.items()
        }

        queue: deque[str] = deque([ref for ref, deg in indegree.items() if deg == 0])
        failure = False

        while queue:
            ref = queue.popleft()
            node = nodes[ref]
            step = steps[ref]

            self._record_step_status(step, "running")
            try:
                output = self._execute_node(node)
                self.outputs[ref] = output
                # Merge simple context updates automatically
                if isinstance(output, dict) and "context" in output and isinstance(
                    output["context"], dict
                ):
                    self.context.update(output["context"])
                self._record_step_status(step, "success", output=output)
                self._log("INFO", f"Node {node.name} completed", node=node, extra=output)
            except WorkflowExecutionError as exc:
                failure = True
                self._record_step_status(step, "failed", error=str(exc))
                self._log("ERROR", str(exc), node=node)
                continue

            for edge in edges_by_source.get(ref, []):
                target_ref = str(edge.target.ref)
                if self._should_traverse(edge, output):
                    indegree[target_ref] = max(indegree.get(target_ref, 1) - 1, 0)
                    if indegree[target_ref] == 0:
                        queue.append(target_ref)
                else:
                    self._log(
                        "DEBUG",
                        f"Edge {edge.id} skipped due to condition/label",
                        node=node,
                        extra={"edge": edge.id},
                    )

        self._mark_unvisited_steps(steps)

        if failure:
            self.run.mark_finished("failed", outputs=self.outputs)
        elif any(step.status == "skipped" for step in steps.values()):
            self.run.mark_finished("partial", outputs=self.outputs)
        else:
            self.run.mark_finished("success", outputs=self.outputs)

        self._log("INFO", f"Workflow run finished with {self.run.status}")
        return self.run
