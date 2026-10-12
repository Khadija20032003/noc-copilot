"""Verifier: checks the draft against the evidence with one structured call (no tools)."""
from __future__ import annotations

import json
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..config import Settings
from . import prompts
from .base import format_findings, format_history, invoke_structured, short
from .state import NocState


class Verdict(BaseModel):
    verdict: Literal["approve", "revise"]
    feedback: str = Field(description="For revise: what is wrong and what is needed. For approve: one short line.")


def make_verifier(llm: BaseChatModel, settings: Settings):
    judge = llm.with_structured_output(Verdict, method="function_calling")

    def verifier(state: NocState) -> dict:
        draft = state["draft"] or {}
        review = (
            f"Conversation so far:\n{format_history(state['messages'])}\n\n"
            f"Question: {state['question']}\n\n"
            f"Draft answer:\n{draft.get('answer', '')}\n\n"
            f"Proposed ticket: {json.dumps(draft.get('proposed_ticket'))}\n\n"
            f"Findings:\n{format_findings(state.get('findings', []), with_tool_results=True)}"
        )
        verdict = invoke_structured(judge, [SystemMessage(prompts.VERIFIER), HumanMessage(review)])
        if verdict is None:
            # No valid verdict: do not approve, and stop revising (finalize adds a caveat, drops the ticket).
            verdict = Verdict(verdict="revise", feedback="The Verifier returned no valid verdict.")
            revisions = settings.max_revisions + 1
        else:
            revisions = state.get("revisions", 0) + (0 if verdict.verdict == "approve" else 1)
        approved = verdict.verdict == "approve"
        trace = state.get("trace", []) + [
            {"agent": "Verifier", "type": "verdict", "detail": f"{verdict.verdict}: {short(verdict.feedback, 240)}"}
        ]
        return {
            "approved": approved,
            "verification_feedback": None if approved else verdict.feedback,
            "revisions": revisions,
            "trace": trace,
        }

    return verifier
