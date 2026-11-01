"""Markdown-aware chunking: split on headings, then windows of `max_words` with `overlap` words of context carried over.
Each chunk keeps the heading path so a citation can say where in the document it came from."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from rag.documents import Document

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


@dataclass
class Chunk:
    id: str
    doc_id: str
    title: str
    collection: str
    url: str
    heading_path: list[str]
    text: str
    position: int
    fictional: bool = False

    @property
    def heading(self) -> str:
        return " › ".join(self.heading_path)

    def to_metadata(self) -> dict:
        return {"doc_id": self.doc_id, "title": self.title, "collection": self.collection, "url": self.url,
                "heading": self.heading, "position": self.position, "fictional": self.fictional, "text": self.text}

    @classmethod
    def from_metadata(cls, chunk_id: str, m: dict) -> "Chunk":
        path = [h for h in str(m.get("heading", "")).split(" › ") if h]
        return cls(id=chunk_id, doc_id=str(m["doc_id"]), title=str(m.get("title", "")), collection=str(m.get("collection", "")), url=str(m.get("url", "")),
                   heading_path=path, text=str(m.get("text", "")), position=int(m.get("position", 0)), fictional=bool(m.get("fictional", False)))


def sections(text: str) -> list[tuple[list[str], str]]:
    """[(heading_path, body)] in document order. Text before the first heading has an empty path."""
    out: list[tuple[list[str], list[str]]] = [([], [])]
    stack: list[tuple[int, str]] = []
    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            level, title = len(m.group(1)), m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            out.append(([t for _, t in stack], []))
        else:
            out[-1][1].append(line)
    return [(path, "\n".join(lines).strip()) for path, lines in out if "\n".join(lines).strip()]


def windows(words: list[str], max_words: int, overlap: int) -> list[list[str]]:
    if len(words) <= max_words:
        return [words] if words else []
    step = max(1, max_words - overlap)
    out, start = [], 0
    while start < len(words):
        out.append(words[start:start + max_words])
        if start + max_words >= len(words):
            break
        start += step
    return out


def chunk_document(doc: Document, max_words: int = 350, overlap: int = 60) -> list[Chunk]:
    chunks: list[Chunk] = []
    for raw_path, body in sections(doc.text):
        path = [h for h in raw_path if h.strip().lower() != doc.title.strip().lower()]
        for w in windows(body.split(), max_words, overlap):
            # the heading path is prepended to the embedded text so a window far down a section still carries its context
            prefix = f"{doc.title}" + (f" — {' › '.join(path)}" if path else "")
            chunks.append(Chunk(id=f"{doc.id}#{len(chunks)}", doc_id=doc.id, title=doc.title, collection=doc.collection, url=doc.url,
                                heading_path=list(path), text=f"{prefix}\n{' '.join(w)}", position=len(chunks), fictional=doc.fictional))
    if not chunks and doc.text.strip():
        chunks.append(Chunk(id=f"{doc.id}#0", doc_id=doc.id, title=doc.title, collection=doc.collection, url=doc.url, heading_path=[],
                            text=f"{doc.title}\n{doc.text.strip()}", position=0, fictional=doc.fictional))
    return chunks


def chunk_corpus(docs: list[Document], max_words: int = 350, overlap: int = 60) -> list[Chunk]:
    return [c for d in docs for c in chunk_document(d, max_words, overlap)]
