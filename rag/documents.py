"""Corpus loading: Markdown files with a small YAML-ish front matter block.

    ---
    id: pm-outputs
    title: Model outputs
    collection: product-docs
    url: https://docs.cybcube.com/...
    tags: [outputs, oep, aal]
    fictional: false
    ---
    # Body in Markdown

Only `key: value` lines are supported in the front matter (strings, booleans, `[a, b]` lists). The collection defaults
to the name of the folder the file sits in."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

COLLECTIONS = ("product-docs", "policies", "faqs")
_FM = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)


@dataclass
class Document:
    id: str
    title: str
    collection: str
    url: str
    text: str
    tags: list[str] = field(default_factory=list)
    fictional: bool = False
    path: str = ""


def parse_front_matter(raw: str) -> tuple[dict, str]:
    """Return (meta, body). Missing front matter -> ({}, raw)."""
    m = _FM.match(raw)
    if not m:
        return {}, raw
    meta: dict = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key] = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
        elif value.lower() in ("true", "false"):
            meta[key] = value.lower() == "true"
        else:
            meta[key] = value.strip("'\"")
    return meta, raw[m.end():]


def load_document(path: Path, collection: str | None = None) -> Document:
    meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
    title = meta.get("title") or next((l.lstrip("# ").strip() for l in body.splitlines() if l.startswith("#")), path.stem)
    return Document(id=str(meta.get("id") or path.stem), title=str(title), collection=str(meta.get("collection") or collection or path.parent.name),
                    url=str(meta.get("url") or f"internal://{path.parent.name}/{path.stem}"), text=body.strip(), tags=list(meta.get("tags") or []),
                    fictional=bool(meta.get("fictional", False)), path=str(path))


def load_corpus(corpus_dir: Path) -> list[Document]:
    """Every `*.md` under `corpus_dir/<collection>/`, sorted by path. Duplicate ids raise: citations must be unambiguous."""
    docs: list[Document] = []
    for path in sorted(Path(corpus_dir).glob("*/*.md")):
        docs.append(load_document(path, collection=path.parent.name))
    seen: dict[str, str] = {}
    for d in docs:
        if d.collection not in COLLECTIONS:
            raise ValueError(f"{d.path}: unknown collection {d.collection!r} (expected one of {COLLECTIONS})")
        if d.id in seen:
            raise ValueError(f"duplicate document id {d.id!r}: {seen[d.id]} and {d.path}")
        seen[d.id] = d.path
    return docs
