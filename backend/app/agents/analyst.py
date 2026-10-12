"""Analyst agent: evidence from network data. Tools: query_network_data and network_calculator."""
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from ..config import Settings
from ..tools import network_calculator, query_network_data
from . import prompts
from .base import as_finding, run_tool_loop, short
from .state import NocState

ANALYST_TOOLS = [query_network_data, network_calculator]


def make_analyst(llm: BaseChatModel, settings: Settings):
    def analyst(state: NocState) -> dict:
        task = state["task"]
        loop = run_tool_loop(llm, ANALYST_TOOLS, prompts.ANALYST, f"Task: {task}", "Analyst",
                             settings.max_tool_iterations)
        trace = state.get("trace", []) + loop.trace + [
            {"agent": "Analyst", "type": "finding", "detail": short(loop.content, 240)}
        ]
        return {"findings": state.get("findings", []) + [as_finding("Analyst", task, loop)], "trace": trace}

    return analyst
