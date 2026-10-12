"""Supervisor: an LLM router with structured output that picks the next agent."""
from __future__ import annotations

from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..config import Settings
from . import prompts
from .base import format_findings, format_history, invoke_structured
from .state import NocState


class RouteDecision(BaseModel):
    """The Supervisor's decision about the next step."""

    next: Literal["research", "analyst", "answer"]
    reason: str = Field(description="One sentence shown to the engineer: why this step")
    task: str = Field(default="", description="Self-contained instruction for the chosen agent (empty for answer)")
    needs_verification: bool = Field(description="True for diagnoses, data numbers, severities, recommendations")


def make_supervisor(llm: BaseChatModel, settings: Settings):
    router = llm.with_structured_output(RouteDecision, method="function_calling")

    def supervisor(state: NocState) -> dict:
        steps = state.get("steps", 0)
        trace = list(state.get("trace", []))
        if steps >= settings.max_steps:
            trace.append({"agent": "Supervisor", "type": "guard",
                          "detail": f"Step limit ({settings.max_steps}) reached: answering with the findings so far."})
            return {"next_step": "answer", "task": "", "trace": trace}

        context = (
            f"Conversation so far:\n{format_history(state['messages'])}\n\n"
            f"Current question: {state['question']}\n\n"
            f"Findings so far:\n{format_findings(state.get('findings', []))}\n\n"
            f"Verifier feedback: {state.get('verification_feedback') or 'none'}\n"
            f"Steps used: {steps} of {settings.max_steps}."
        )
        decision = invoke_structured(router, [SystemMessage(prompts.SUPERVISOR), HumanMessage(context)])
        if decision is None:
            trace.append({"agent": "Supervisor", "type": "guard",
                          "detail": "Routing output was invalid twice: answering with the findings so far."})
            return {"next_step": "answer", "task": "", "steps": steps + 1, "trace": trace}
        trace.append({"agent": "Supervisor", "type": "routing",
                      "detail": f"-> {decision.next}: {decision.reason}"})
        return {
            "next_step": decision.next,
            "task": decision.task or state["question"],
            # Sticky: once any decision says the answer needs checking, it stays checked.
            "needs_verification": state.get("needs_verification", False) or decision.needs_verification,
            "steps": steps + 1,
            "trace": trace,
        }

    return supervisor
