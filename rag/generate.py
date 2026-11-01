"""Answer generation with citations. The generator only ever sees the retrieved passages, numbered [1]..[k], and must
cite by number. `cited_numbers` extracts the numbers actually used so the response can list only those sources."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from rag.store import Hit

NOT_FOUND = "I could not find this in the indexed documents."
_CITE = re.compile(r"\[([\d,\s\-–]+)\]")
_SENT = re.compile(r"(?<=[.!?])\s+")

SYSTEM_PROMPT = """You answer questions for employees using ONLY the numbered passages provided. Rules:
- Every sentence that states a fact must end with the citation of the passage it came from, like [2]. Use several, like [1][3], when needed.
- Use only the passage numbers given. Never invent a number, a figure, or a policy that is not in the passages.
- If the passages do not contain the answer, reply exactly: "I could not find this in the indexed documents." and nothing else.
- Be concise: two to five sentences. Prefer the passage's own terms (table names, report names, field names) over paraphrase.
- Passages marked FICTIONAL are demo content; treat them as the policy or FAQ they describe."""


@dataclass
class Citation:
    n: int
    chunk_id: str
    doc_id: str
    title: str
    collection: str
    url: str
    heading: str
    snippet: str
    score: float
    fictional: bool = False


@dataclass
class Answer:
    question: str
    text: str
    citations: list[Citation] = field(default_factory=list)     # only the [n] the answer used, in order of first use
    sources: list[Citation] = field(default_factory=list)       # everything retrieved, in rank order
    alpha: float = 0.5
    mode: str = "local"
    generator: str = "extractive"
    found: bool = True


def cited_numbers(text: str, limit: int) -> list[int]:
    """[n], [1][3], [1, 3] and [1-3] markers in order of first use; numbers outside 1..limit are ignored."""
    out: list[int] = []
    for m in _CITE.finditer(text):
        for part in re.split(r"[,\s]+", m.group(1).replace("–", "-")):
            if not part:
                continue
            lo, _, hi = part.partition("-")
            if not lo.isdigit() or (hi and not hi.isdigit()):
                continue
            for n in range(int(lo), int(hi or lo) + 1):
                if 1 <= n <= limit and n not in out:
                    out.append(n)
    return out


def evidence(h: Hit) -> float:
    """How well a hit matches, independent of the alpha the user chose: the hybrid score at alpha 0.5 when the store
    reports both components, else the store's own score. Used only to decide whether to answer at all."""
    if h.dense is None and h.sparse is None:
        return h.score
    return 0.5 * max(h.dense or 0.0, 0.0) + 0.5 * max(h.sparse or 0.0, 0.0)


def snippet(text: str, words: int = 40) -> str:
    body = text.split("\n", 1)[1] if "\n" in text else text
    w = body.split()
    return " ".join(w[:words]) + (" …" if len(w) > words else "")


def passages_block(hits: list[Hit]) -> str:
    parts = []
    for n, h in enumerate(hits, start=1):
        c = h.chunk
        tag = " (FICTIONAL demo content)" if c.fictional else ""
        where = f" › {c.heading}" if c.heading else ""
        parts.append(f"[{n}] {c.title}{where} — collection: {c.collection}{tag}\n{c.text.split(chr(10), 1)[-1]}")
    return "\n\n".join(parts)


class Generator(Protocol):
    name: str

    def generate(self, question: str, hits: list[Hit], coverage: float = 1.0) -> str: ...


class ExtractiveGenerator:
    """No model: the first sentences of the top passages, each followed by its citation. Honest about what it is."""
    name = "extractive"

    def __init__(self, max_passages: int = 3, sentences: int = 2, min_score: float = 0.15, min_coverage: float = 0.5):
        self.max_passages, self.sentences, self.min_score, self.min_coverage = max_passages, sentences, min_score, min_coverage

    def generate(self, question: str, hits: list[Hit], coverage: float = 1.0) -> str:
        # Two alpha-independent checks: the best passage must carry real evidence, and more than half of the question's
        # content words must exist in the corpus at all ("parental leave policy" shares only "policy" with it); at exactly
        # half, the evidence floor decides.
        if not hits or max(evidence(h) for h in hits) < self.min_score or coverage < self.min_coverage:
            return NOT_FOUND                          # nothing matched convincingly: say so rather than quote the least-bad passage
        lines = []
        for n, h in enumerate(hits[: self.max_passages], start=1):
            if evidence(h) < self.min_score:
                continue
            body = h.chunk.text.split("\n", 1)[-1].strip()
            sents = [s.strip() for s in _SENT.split(body) if s.strip()][: self.sentences]
            if sents:
                txt = " ".join(sents)
                lines.append((txt if txt[-1] in ".!?" else txt + ".") + f" [{n}]")
        return " ".join(lines) if lines else NOT_FOUND


class OpenAIGenerator:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", client=None):
        from openai import OpenAI
        self.name = model
        self._client = client or OpenAI(api_key=api_key)

    def generate(self, question: str, hits: list[Hit], coverage: float = 1.0) -> str:
        if not hits:
            return NOT_FOUND
        user = f"Question: {question}\n\nPassages:\n\n{passages_block(hits)}"
        resp = self._client.chat.completions.create(model=self.name, temperature=0, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}])
        return (resp.choices[0].message.content or "").strip() or NOT_FOUND
