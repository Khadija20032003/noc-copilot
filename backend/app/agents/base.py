"""Shared helpers: a small tool-calling loop and prompt formatting."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from pydantic import ValidationError

from .state import Finding, TraceEntry


def short(text: Any, limit: int = 160) -> str:
    """One-line preview for the trace."""
    s = " ".join(str(text).split())
    return s if len(s) <= limit else s[: limit - 3] + "..."


@dataclass
class LoopResult:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    trace: list[TraceEntry] = field(default_factory=list)


def execute_tool(tools: dict[str, BaseTool], call: dict) -> ToolMessage:
    """Run one tool call. Errors are returned to the agent as a message, never raised."""
    tool = tools.get(call["name"])
    if tool is None:
        return ToolMessage(f"Error: tool '{call['name']}' is not available to this agent.",
                           tool_call_id=call["id"], status="error")
    try:
        return tool.invoke(call)
    except Exception as exc:  # noqa: BLE001 (bad arguments, validation errors)
        return ToolMessage(f"Error: {exc}", tool_call_id=call["id"], status="error")


def run_tool_loop(llm: BaseChatModel, tools: list[BaseTool], system: str, task: str, agent: str,
                  max_iterations: int) -> LoopResult:
    """ReAct-style loop: the model calls tools until it answers in plain text or the budget runs out."""
    by_name = {t.name: t for t in tools}
    model = llm.bind_tools(tools)
    messages: list[AnyMessage] = [SystemMessage(system), HumanMessage(task)]
    result = LoopResult(content="")
    ai: AIMessage | None = None
    for _ in range(max_iterations):
        ai = model.invoke(messages)
        messages.append(ai)
        if not ai.tool_calls:
            break
        for call in ai.tool_calls:
            msg = execute_tool(by_name, call)
            messages.append(msg)
            artifact = getattr(msg, "artifact", None)
            if isinstance(artifact, list):
                result.sources += [s for s in artifact if s not in result.sources]
            output = msg.text
            result.tool_calls.append({"tool": call["name"], "args": call["args"], "result": output[:8000]})
            preview = f"{len(artifact)} sections: {', '.join(artifact)}" if isinstance(artifact, list) else short(output)
            result.trace.append({"agent": agent, "type": "tool_call",
                                 "detail": f"{call['name']}({json.dumps(call['args'])}) -> {preview}"})
    else:
        # Budget exhausted while still calling tools: ask once more for the finding.
        messages.append(HumanMessage("Tool budget used up. Write your finding now from the results above."))
        ai = model.invoke(messages)
    content = ai.text.strip() if ai is not None else ""
    result.content = content or "No finding produced (tool budget exhausted). Raw results are in the trace."
    return result


def invoke_structured(runnable: Any, messages: list[AnyMessage], attempts: int = 2) -> Any | None:
    """Call a structured-output model, retrying once on an invalid or missing output.

    Function calling is not strict, so a model can return a bad enum value or omit a field.
    Returns None if every attempt failed; the caller then uses a safe fallback instead of failing the turn.
    """
    for _ in range(attempts):
        try:
            out = runnable.invoke(messages)
        except (OutputParserException, ValidationError):
            continue
        if out is not None:
            return out
    return None


def as_finding(agent: str, task: str, loop: LoopResult) -> Finding:
    return {"agent": agent, "task": task, "content": loop.content, "sources": loop.sources,
            "tool_calls": loop.tool_calls}


def format_history(messages: list[AnyMessage], max_messages: int = 6, max_chars: int = 4000) -> str:
    """Previous turns (excluding the current question) as plain text.

    max_chars is large enough for a full diagnosis (cause, evidence, action, severity), which follow-ups
    such as "and what severity should that be?" depend on.
    """
    previous = messages[:-1][-max_messages:]
    if not previous:
        return "(no previous turns)"
    return "\n".join(f"{'Engineer' if m.type == 'human' else 'Copilot'}: {short(m.text, max_chars)}" for m in previous)


def format_findings(findings: list[Finding], with_tool_results: bool = False) -> str:
    """Findings as plain text for the next prompt."""
    if not findings:
        return "(no findings yet)"
    blocks = []
    for i, f in enumerate(findings, 1):
        block = f"[{i}] {f['agent']} (task: {f['task']})\n{f['content']}"
        if f["sources"]:
            block += "\nRetrieved sources: " + "; ".join(f["sources"])
        if with_tool_results and f["tool_calls"]:
            block += "\nTool results:\n" + "\n".join(
                f"- {c['tool']}({json.dumps(c['args'])}):\n{c['result']}" for c in f["tool_calls"]
            )
        blocks.append(block)
    return "\n\n".join(blocks)
