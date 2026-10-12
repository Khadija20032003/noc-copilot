"""LangGraph wiring: Supervisor -> {Research, Analyst} -> ... -> Answer -> Verifier -> finalize.

    START -> supervisor --research--> research --> supervisor
                        --analyst---> analyst  --> supervisor
                        --answer----> answer --(needs check)--> verifier --approve--> finalize -> END
                                             --(no check)-----> finalize      --revise---> supervisor
"""
from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .agents import make_analyst, make_answer, make_research, make_supervisor, make_verifier
from .agents.state import NocState, new_turn
from .config import Settings, get_settings


def route_from_supervisor(state: NocState) -> str:
    return state["next_step"]


def route_after_answer(state: NocState) -> str:
    """Verify diagnoses, numbers and anything carrying a ticket; skip simple answers.

    A rewrite after a revise verdict is always re-checked, even if it no longer carries a ticket.
    """
    draft = state.get("draft") or {}
    needs_check = state.get("needs_verification") or draft.get("proposed_ticket") or state.get("approved") is False
    return "verifier" if needs_check else "finalize"


def make_route_after_verifier(settings: Settings):
    def route_after_verifier(state: NocState) -> str:
        if state.get("approved"):
            return "finalize"
        return "supervisor" if state.get("revisions", 0) <= settings.max_revisions else "finalize"

    return route_after_verifier


def finalize(state: NocState) -> dict:
    """Publish the answer. An unverified diagnosis gets a caveat and loses its proposed ticket."""
    draft = state.get("draft") or {}
    answer = draft.get("answer") or "I could not produce an answer."
    ticket = draft.get("proposed_ticket")
    trace = list(state.get("trace", []))
    if state.get("approved") is False:
        answer += ("\n\n> Caveat: the Verifier did not approve this answer. "
                   f"Open issue: {state.get('verification_feedback')}")
        if ticket:
            answer += "\n\n> The proposed ticket was withheld because the answer was not verified."
            trace.append({"agent": "Verifier", "type": "guard",
                          "detail": "Proposed ticket withheld because the answer was not approved."})
        ticket = None
    return {
        "messages": [AIMessage(answer)],
        "final_answer": answer,
        "sources": draft.get("sources", []),
        "proposed_ticket": ticket,
        "root_cause_id": draft.get("root_cause_id"),
        "trace": trace,
    }


def build_graph(llm: BaseChatModel, settings: Settings | None = None,
                checkpointer: BaseCheckpointSaver | None = None):
    """Compile the multi-agent graph. The checkpointer keeps conversation state per thread_id."""
    s = settings or get_settings()
    g = StateGraph(NocState)
    g.add_node("supervisor", make_supervisor(llm, s))
    g.add_node("research", make_research(llm, s))
    g.add_node("analyst", make_analyst(llm, s))
    g.add_node("answer", make_answer(llm))
    g.add_node("verifier", make_verifier(llm, s))
    g.add_node("finalize", finalize)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", route_from_supervisor, ["research", "analyst", "answer"])
    g.add_edge("research", "supervisor")
    g.add_edge("analyst", "supervisor")
    g.add_conditional_edges("answer", route_after_answer, ["verifier", "finalize"])
    g.add_conditional_edges("verifier", make_route_after_verifier(s), ["supervisor", "finalize"])
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer if checkpointer is not None else MemorySaver())


def recursion_limit(s: Settings) -> int:
    """Upper bound on node runs per turn: max_steps (supervisor + agent) pairs, then per review round
    one guard supervisor call, answer and verifier, plus finalize; with a small margin."""
    return 2 * s.max_steps + 3 * (s.max_revisions + 1) + 5


def run_turn(graph, session_id: str, message: str, settings: Settings | None = None) -> dict[str, Any]:
    """Run one user turn on a thread and return the API payload (plus eval-only fields).

    Pass the same settings the graph was built with if they differ from the environment."""
    limit = recursion_limit(settings or get_settings())
    config = {"configurable": {"thread_id": session_id}, "recursion_limit": limit}
    state = graph.invoke(new_turn(message), config)
    return {
        "answer": state["final_answer"],
        "sources": state.get("sources", []),
        "trace": state.get("trace", []),
        "proposed_ticket": state.get("proposed_ticket"),
        "verified": state.get("approved"),
        # Not part of the API contract; used by the evaluation harness.
        "root_cause_id": state.get("root_cause_id"),
        "approved": state.get("approved"),
        "steps": state.get("steps", 0),
    }
