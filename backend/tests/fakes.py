"""A scripted stand-in for a chat model, so the graph runs in tests without an API key.

Responses are queued per role. Tool-loop calls are keyed by the agent (detected from its system
prompt); structured-output calls are keyed by the schema name (RouteDecision, DraftAnswer, Verdict).
"""
from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

ROLE_MARKERS = {
    "research": "You are the Research agent",
    "analyst": "You are the Analyst agent",
}


def tool_call(name: str, call_id: str = "call_1", **args: Any) -> AIMessage:
    """An AIMessage that requests one tool call."""
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


class ScriptedLLM:
    def __init__(self, scripts: dict[str, list[Any]]):
        self.scripts = {k: list(v) for k, v in scripts.items()}
        self.calls: list[tuple[str, list]] = []  # (key, messages) for assertions

    def _pop(self, key: str, messages: list) -> Any:
        self.calls.append((key, messages))
        queue = self.scripts.get(key)
        if not queue:
            raise AssertionError(f"No scripted response left for '{key}'")
        item = queue.pop(0)
        if isinstance(item, Exception):  # simulate an invalid structured output
            raise item
        return item

    def bind_tools(self, tools: list, **_: Any) -> "_Runnable":
        return _Runnable(self, None)

    def with_structured_output(self, schema: type, **_: Any) -> "_Runnable":
        return _Runnable(self, schema.__name__)

    def remaining(self) -> dict[str, int]:
        return {k: len(v) for k, v in self.scripts.items() if v}


class _Runnable:
    def __init__(self, llm: ScriptedLLM, key: str | None):
        self.llm, self.key = llm, key

    def invoke(self, messages: list, *_: Any, **__: Any) -> Any:
        key = self.key
        if key is None:
            system = messages[0].content
            key = next(role for role, marker in ROLE_MARKERS.items() if marker in system)
        return self.llm._pop(key, messages)
