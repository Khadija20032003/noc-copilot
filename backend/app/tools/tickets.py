"""Ticket model and JSON ticket store.

Human in the loop: no agent can create a ticket. The Answer step only PROPOSES one; the API saves
it when the engineer clicks Approve (POST /api/tickets).
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ..config import get_settings

# Literal so an invalid value (e.g. "RC6 PCI conflict") fails validation and the structured call is retried.
RootCauseId = Literal["RC1", "RC2", "RC3", "RC4", "RC5", "RC6", "RC7", "RC8"]


class TicketDraft(BaseModel):
    """A NordTel incident ticket as proposed by the assistant (fields from escalation_policy.md)."""

    severity: Literal["P1", "P2", "P3", "P4"]
    pci: int = Field(description="Serving PCI of the affected cell")
    neighbor_pci: int | None = Field(default=None, description="Neighbor PCI involved, if any")
    site_name: str
    symptom: str
    evidence: str = Field(description="Measured KPI values with time range")
    root_cause_id: RootCauseId | Literal["unknown"] = Field(description="RC1 to RC8, or 'unknown'")
    recommended_action: str = Field(description="Action and the team that should act")
    confidence: Literal["high", "medium", "low"]


class StoredTicket(TicketDraft):
    id: str
    created_at: str
    status: Literal["open"] = "open"


_lock = threading.Lock()


def _path() -> Path:
    return Path(get_settings().tickets_path)


def list_tickets() -> list[dict]:
    path = _path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_ticket(draft: TicketDraft) -> StoredTicket:
    """Append an approved ticket to the JSON store."""
    ticket = StoredTicket(
        **draft.model_dump(),
        id=f"NT-{uuid.uuid4().hex[:8].upper()}",
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    with _lock:
        tickets = list_tickets()
        tickets.append(ticket.model_dump())
        path = _path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(tickets, indent=2), encoding="utf-8")
    return ticket

