"""Graph state shared by all agents."""
from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph.message import add_messages


class Finding(TypedDict):
    agent: str
    task: str
    content: str
    sources: list[str]
    tool_calls: list[dict[str, Any]]


class TraceEntry(TypedDict):
    agent: str
    type: str      # routing | tool_call | finding | answer | verdict | guard
    detail: str


class NocState(TypedDict, total=False):
    # Conversation, persisted per thread by the checkpointer (appended through add_messages).
    messages: Annotated[list[AnyMessage], add_messages]
    # Per-question fields: overwritten (reset) by the API input at the start of every turn.
    question: str
    findings: list[Finding]
    trace: list[TraceEntry]
    next_step: str
    task: str
    needs_verification: bool
    verification_feedback: str | None
    revisions: int
    steps: int
    draft: dict[str, Any] | None
    approved: bool | None
    final_answer: str
    sources: list[str]
    proposed_ticket: dict[str, Any] | None
    root_cause_id: str | None


def new_turn(question: str) -> dict[str, Any]:
    """Input for one user turn: appends the question and resets every per-question field."""
    return {
        "messages": [HumanMessage(question)], "question": question, "findings": [], "trace": [],
        "next_step": "", "task": "", "needs_verification": False, "verification_feedback": None,
        "revisions": 0, "steps": 0, "draft": None, "approved": None, "final_answer": "",
        "sources": [], "proposed_ticket": None, "root_cause_id": None,
    }
