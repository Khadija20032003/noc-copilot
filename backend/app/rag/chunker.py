"""Split knowledge base documents into one chunk per H2 section."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Chunk:
    doc: str        # file name, e.g. "runbook_interference.md"
    title: str      # document H1 title
    section: str    # H2 section title
    text: str       # section body (with its H3 subsections)

    @property
    def source(self) -> str:
        return f"{self.doc} > {self.section}"

    @property
    def search_text(self) -> str:
        """Text indexed for retrieval: doc title + section title + body."""
        return f"{self.title}\n{self.section}\n{self.text}"


def chunk_markdown(doc: str, markdown: str) -> list[Chunk]:
    """One chunk per H2 section; the intro before the first H2 becomes an 'Overview' chunk.

    The "Related documents" section is skipped: it is a list of file names and only adds noise.
    """
    title_match = re.search(r"^# (.+)$", markdown, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else doc
    parts = re.split(r"^## (.+)$", markdown, flags=re.MULTILINE)
    chunks = []
    intro = re.sub(r"^# .+$", "", parts[0], flags=re.MULTILINE).strip()
    if intro:
        chunks.append(Chunk(doc, title, "Overview", intro))
    for section, body in zip(parts[1::2], parts[2::2]):
        section = section.strip()
        if section.lower() == "related documents" or not body.strip():
            continue
        chunks.append(Chunk(doc, title, section, body.strip()))
    return chunks


def load_chunks(kb_dir: Path) -> list[Chunk]:
    """Load and chunk every markdown file in the knowledge base directory."""
    chunks: list[Chunk] = []
    for path in sorted(Path(kb_dir).glob("*.md")):
        chunks.extend(chunk_markdown(path.name, path.read_text(encoding="utf-8")))
    return chunks
