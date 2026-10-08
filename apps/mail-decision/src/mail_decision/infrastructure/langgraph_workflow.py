"""LangGraph adapter for the mail-decision processing-step workflow."""

import logging
from time import perf_counter
from collections.abc import Callable
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from mail_sort_logging import add_log_context

from mail_decision.processing.context import DailyRequestLimitReached, ProcessingContext
from mail_decision.processing.ports import ProcessingWorkflow
from mail_decision.processing.statistics.diagnostics import DiagnosticScope
from mail_decision.processing.steps.interface import ProcessingStep


logger = logging.getLogger(__name__)


class _WorkflowState(TypedDict):
    context: ProcessingContext
    diagnostics: DiagnosticScope | None


class LangGraphWorkflow(ProcessingWorkflow):
    """Run existing processing steps as a graph, without owning job retries or persistence."""

    def __init__(self, steps: list[ProcessingStep]) -> None:
        if not steps:
            raise ValueError("LangGraph workflow requires at least one processing step")

        builder = StateGraph(_WorkflowState)
        node_names = [
            f"step_{index}_{type(step).__name__.lower()}"
            for index, step in enumerate(steps, start=1)
        ]
        for index, (step, node_name) in enumerate(zip(steps, node_names, strict=True), start=1):
            builder.add_node(node_name, self._node(step, index))
            next_node = node_names[index] if index < len(node_names) else END
            if next_node == END:
                builder.add_edge(node_name, END)
            else:
                builder.add_conditional_edges(
                    node_name,
                    self._next_step,
                    {"continue": next_node, "finish": END},
                )

        builder.add_edge(START, node_names[0])
        self._graph = builder.compile()

    def execute(
        self,
        context: ProcessingContext,
        diagnostics: DiagnosticScope | None,
    ) -> None:
        # No checkpointer: PostgreSQL jobs own durable retries and recovery. A graph
        # attempt is short-lived and safe to restart from its first read-only step.
        self._graph.invoke({"context": context, "diagnostics": diagnostics})

    @staticmethod
    def _next_step(state: _WorkflowState) -> str:
        return "finish" if state["context"].outcome is not None else "continue"

    @staticmethod
    def _node(
        step: ProcessingStep,
        number: int,
    ) -> Callable[[_WorkflowState], dict[str, ProcessingContext]]:
        name = type(step).__name__

        def execute(state: _WorkflowState) -> dict[str, ProcessingContext]:
            context = state["context"]
            diagnostics = state["diagnostics"]
            context.last_step = name
            if diagnostics is not None:
                diagnostics.step = name
                diagnostics.step_number = number
                diagnostics.destinations = set(context.destinations)

            started = perf_counter()
            if diagnostics is not None:
                diagnostics.record("step", status="started", details={})
            logger.info(
                "step started: job_id=%s step=%s name=%s",
                context.job.id, number, name,
            )
            try:
                step.execute(context)
                if context.email is not None:
                    add_log_context(subject=context.email.subject)
            except Exception as error:
                if diagnostics is not None:
                    diagnostics.record(
                        "step",
                        status="deferred" if isinstance(error, DailyRequestLimitReached) else "failed",
                        details={
                            "error_type": type(error).__name__,
                            "duration_seconds": perf_counter() - started,
                            "last_step": name,
                            "decision_step": context.decision_step,
                            "finalization": "not_started",
                        },
                    )
                raise

            if context.outcome is not None:
                context.decision_step = name
            if diagnostics is not None:
                diagnostics.record(
                    "step",
                    status="decision_made" if context.decision_step else "completed",
                    details={
                        "duration_seconds": perf_counter() - started,
                        "decision_step": context.decision_step,
                        "last_step": name,
                        "destination_id": context.outcome.destination_id if context.outcome else None,
                        "outcome_status": context.outcome.status if context.outcome else None,
                    },
                )
            return {"context": context}

        return execute
