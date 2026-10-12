"""HTTP routes: /api/chat (multi-agent graph) and /api/tickets (human-approved tickets)."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel, Field

from .graph import build_graph, run_turn
from .llm import MissingAPIKeyError, get_chat_model
from .tools.tickets import TicketDraft, list_tickets, save_ticket

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)


class TraceItem(BaseModel):
    agent: str
    type: str
    detail: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    trace: list[TraceItem]
    proposed_ticket: TicketDraft | None
    # The Verifier's last verdict: True approved, False not approved, None if verification was skipped.
    verified: bool | None


@lru_cache
def get_graph():
    """One compiled graph per process; its MemorySaver holds all conversations in memory."""
    return build_graph(get_chat_model())


def error(status: int, code: str, message: str) -> JSONResponse:
    """Error body: `detail` is the human-readable message, `error` a stable code."""
    return JSONResponse(status_code=status, content={"error": code, "detail": message})


def missing_key_handler(_request, exc: MissingAPIKeyError) -> JSONResponse:
    return error(503, "llm_not_configured", str(exc))


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, graph=Depends(get_graph)) -> Any:
    """Run one turn. The graph (and the LLM) is only created here, so the rest works without a key."""
    try:
        result = run_turn(graph, req.session_id, req.message)
    except GraphRecursionError:
        log.exception("chat hit the graph step limit")
        return error(500, "step_limit", "The agents did not finish within the step limit; see server logs.")
    except Exception:  # noqa: BLE001 (LLM provider errors, network)
        # Details stay in the server log: provider errors can contain request ids or key fragments.
        log.exception("chat failed")
        return error(502, "llm_error", "The assistant failed to answer; see server logs.")
    return {k: result[k] for k in ("answer", "sources", "trace", "proposed_ticket", "verified")}


@router.post("/tickets")
def approve_ticket(ticket: TicketDraft) -> dict:
    """Called when the engineer clicks Approve: the only path that creates a ticket."""
    return save_ticket(ticket).model_dump()


@router.get("/tickets")
def get_tickets() -> list[dict]:
    return list_tickets()
