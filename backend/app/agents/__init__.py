"""Agents: Supervisor (router), Research, Analyst, Answer step and Verifier.

Tool permissions (least privilege): Research gets search_knowledge_base only, the Analyst
gets query_network_data and network_calculator, the Supervisor, Answer step and
Verifier get no tools, and no agent can create a ticket (only the API does, after the engineer approves).
"""
from .analyst import ANALYST_TOOLS, make_analyst
from .answer import DraftAnswer, make_answer
from .research import RESEARCH_TOOLS, make_research
from .supervisor import RouteDecision, make_supervisor
from .verifier import Verdict, make_verifier

__all__ = [
    "ANALYST_TOOLS", "RESEARCH_TOOLS", "DraftAnswer", "RouteDecision", "Verdict",
    "make_analyst", "make_answer", "make_research", "make_supervisor", "make_verifier",
]
