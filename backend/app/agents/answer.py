"""Answer step: composes the draft answer (and an optional proposed ticket) from the findings."""
from __future__ import annotations

from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..tools.tickets import RootCauseId, TicketDraft
from . import prompts
from .base import format_findings, format_history, invoke_structured, short
from .state import NocState


class DraftAnswer(BaseModel):
    answer: str = Field(description="Final answer in Markdown, with inline citations (file.md > Section)")
    sources: list[str] = Field(default_factory=list, description="Cited sources, 'file.md > Section'")
    root_cause_id: RootCauseId | Literal["unknown"] | None = Field(
        default=None, description="Primary root cause RC1 to RC8 for a diagnosis, or 'unknown'")
    proposed_ticket: TicketDraft | None = Field(default=None, description="Only for a diagnosis with data evidence")


def retrieved_sources(state: NocState) -> list[str]:
    seen: list[str] = []
    for f in state.get("findings", []):
        seen += [s for s in f["sources"] if s not in seen]
    return seen


def keep_retrieved(sources: list[str], retrieved: list[str]) -> list[str]:
    """Keep only sources that were actually retrieved this turn (ignoring case and spacing)."""
    known = {" ".join(s.split()).casefold(): s for s in retrieved}
    cited: list[str] = []
    for label in sources:
        source = known.get(" ".join(label.split()).casefold())
        if source and source not in cited:
            cited.append(source)
    return cited


def fallback_draft(state: NocState) -> DraftAnswer:
    """Used when the model returns no valid DraftAnswer twice: show the findings instead of failing."""
    findings = "\n\n".join(f["content"] for f in state.get("findings", []))
    return DraftAnswer(answer="I could not format a complete answer. " + (
        f"Findings so far:\n\n{findings}" if findings else "Please rephrase the question."))


def make_answer(llm: BaseChatModel):
    writer = llm.with_structured_output(DraftAnswer, method="function_calling")

    def answer(state: NocState) -> dict:
        context = (
            f"Conversation so far:\n{format_history(state['messages'])}\n\n"
            f"Question: {state['question']}\n\n"
            f"Findings:\n{format_findings(state.get('findings', []), with_tool_results=True)}\n\n"
            f"Verifier feedback to address: {state.get('verification_feedback') or 'none'}"
        )
        draft = invoke_structured(writer, [SystemMessage(prompts.ANSWER), HumanMessage(context)])
        draft = draft or fallback_draft(state)
        # Only sections actually retrieved this turn may be listed as sources (no hallucinated sources).
        cited = keep_retrieved(draft.sources, retrieved_sources(state))
        ticket = draft.proposed_ticket.model_dump() if draft.proposed_ticket else None
        detail = f"Draft written ({len(cited)} sources" + (", proposed ticket" if ticket else "") + ")"
        return {
            "draft": {"answer": draft.answer, "sources": cited, "proposed_ticket": ticket,
                      "root_cause_id": draft.root_cause_id},
            "trace": state.get("trace", []) + [{"agent": "Answer", "type": "answer", "detail": short(detail)}],
        }

    return answer
