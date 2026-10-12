"""Chunker and BM25 retriever."""
from app.config import get_settings
from app.rag import chunk_markdown, get_retriever, load_chunks
from app.rag.retriever import tokenize

DOC = """# Title

This document is a test.

## First section
Alpha beta.

### Sub
Gamma.

## Related documents
- other.md
"""


def test_chunk_by_h2_keeps_metadata_and_subsections():
    chunks = chunk_markdown("t.md", DOC)
    assert [c.section for c in chunks] == ["Overview", "First section"]
    assert chunks[1].source == "t.md > First section"
    assert "Gamma" in chunks[1].text
    assert chunks[1].search_text.startswith("Title")


def test_all_documents_chunked():
    chunks = load_chunks(get_settings().kb_dir)
    assert {c.doc for c in chunks} == {p.name for p in get_settings().kb_dir.glob("*.md")}
    assert len({c.doc for c in chunks}) == 8


def test_tokenizer_keeps_acronyms_and_numbers():
    assert tokenize("What is SS-RSRP below -105 for RC6?") == ["ss", "rsrp", "below", "105", "rc6"]


def test_retrieval_finds_expected_sections():
    r = get_retriever()
    assert r.search("PCI mod 30 conflict", k=4)[0][0].doc in {"runbook_interference.md", "5g_basics.md"}
    assert r.search("P2 Major severity response time", k=1)[0][0].doc == "escalation_policy.md"
    assert r.search("ping-pong handover", k=4)[0][0].doc in {"handover_basics.md", "kpi_glossary.md"}
    assert r.search("the of and", k=4) == []
