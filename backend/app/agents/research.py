"""Research agent: answers from the knowledge base. Tools: search_knowledge_base only."""
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from ..config import Settings
from ..tools import search_knowledge_base
from . import prompts
from .base import as_finding, run_tool_loop, short
from .state import NocState

RESEARCH_TOOLS = [search_knowledge_base]


def make_research(llm: BaseChatModel, settings: Settings):
    def research(state: NocState) -> dict:
        task = state["task"]
        loop = run_tool_loop(llm, RESEARCH_TOOLS, prompts.RESEARCH, f"Task: {task}", "Research",
                             settings.max_tool_iterations)
        trace = state.get("trace", []) + loop.trace + [
            {"agent": "Research", "type": "finding", "detail": short(loop.content, 240)}
        ]
        return {"findings": state.get("findings", []) + [as_finding("Research", task, loop)], "trace": trace}

    return research
