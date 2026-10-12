"""search_knowledge_base tool (Research agent)."""
from __future__ import annotations

from langchain_core.tools import tool

from ..rag import get_retriever


@tool(response_format="content_and_artifact")
def search_knowledge_base(query: str, k: int = 4) -> tuple[str, list[str]]:
    """Search the NordTel knowledge base (runbooks RC1 to RC8, KPI glossary, handover basics,
    5G basics, escalation policy P1 to P4) with BM25 keyword search.

    Use precise telecom terms in the query, e.g. "PCI mod 30 conflict confirm", "RC8 low scheduled
    resources", "P2 Major severity". Returns the top k sections, each labelled with its source
    "file.md > Section". Cite these sources in your answer.
    """
    k = max(1, min(int(k), 8))
    hits = get_retriever().search(query, k=k)
    if not hits:
        return "No matching sections. Try other keywords.", []
    blocks = [f"[source: {chunk.source}]\n{chunk.text}" for chunk, _ in hits]
    return "\n\n---\n\n".join(blocks), [chunk.source for chunk, _ in hits]
