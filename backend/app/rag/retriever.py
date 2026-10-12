"""BM25 retriever: lexical search suits a tiny corpus full of exact telecom terms (RSRP, PCI mod 30, RC6)."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from rank_bm25 import BM25Okapi

from ..config import get_settings
from .chunker import Chunk, load_chunks

STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i in is it its of on or should that the this "
    "to what when which why with my me we our you your there their be been was were will".split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens without stopwords ('SS-RSRP' -> ['ss', 'rsrp'], 'RC6' -> ['rc6'])."""
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


class BM25Retriever:
    def __init__(self, chunks: list[Chunk]):
        if not chunks:
            raise ValueError("Knowledge base is empty")
        self.chunks = chunks
        self._bm25 = BM25Okapi([tokenize(c.search_text) for c in chunks])

    def search(self, query: str, k: int = 4) -> list[tuple[Chunk, float]]:
        """Top-k chunks with their BM25 score (zero-score chunks are dropped)."""
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [(self.chunks[i], float(scores[i])) for i in ranked if scores[i] > 0]


@lru_cache
def get_retriever(kb_dir: Path | None = None) -> BM25Retriever:
    """Cached retriever over the configured knowledge base."""
    return BM25Retriever(load_chunks(kb_dir or get_settings().kb_dir))
