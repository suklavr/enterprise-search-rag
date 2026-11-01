"""Sparse (keyword) side of hybrid search: a BM25 encoder fitted on the corpus.

Why not a library: Pinecone sparse vectors need integer indices and float values; building the vocabulary here keeps
the ids stable between ingest and query and lets identifiers like `cat_spofimportancelevelfallback` or `i38` be whole
tokens. Document vectors hold BM25 term weights, query vectors hold idf per term; both are L2-normalised so the sparse
dot product lives in [0, 1] like the cosine of unit dense vectors — that is what makes `alpha` a fair weight."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

TOKEN = re.compile(r"[a-z0-9_]+")
STOPWORDS = frozenset("""a an and are as at be by for from has have in into is it its of on or that the this to was were will with
you your we our can do does if not no so than then there these those what when where which who why how all any each
may must should would could also about after before over under between such only more most other some""".split())


def stem(tok: str) -> str:
    """Very light suffix stripping for plain words (never for identifiers with digits or underscores)."""
    if len(tok) <= 4 or not tok.isalpha():
        return tok
    for suffix, repl in (("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if tok.endswith(suffix) and len(tok) - len(suffix) >= 3:
            return tok[: -len(suffix)] + repl
    return tok


def tokenize(text: str) -> list[str]:
    return [stem(t) for t in TOKEN.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


@dataclass
class SparseVector:
    indices: list[int] = field(default_factory=list)
    values: list[float] = field(default_factory=list)

    def as_dict(self) -> dict[int, float]:
        return dict(zip(self.indices, self.values))

    def __bool__(self) -> bool:
        return bool(self.indices)


def _unit(pairs: dict[int, float]) -> SparseVector:
    norm = math.sqrt(sum(v * v for v in pairs.values()))
    if not norm:
        return SparseVector()
    items = sorted(pairs.items())
    return SparseVector([i for i, _ in items], [v / norm for _, v in items])


class BM25Encoder:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.vocab: dict[str, int] = {}
        self.idf: list[float] = []
        self.avgdl: float = 0.0
        self.n_docs: int = 0

    def fit(self, texts: list[str]) -> "BM25Encoder":
        docs = [tokenize(t) for t in texts]
        df: Counter[str] = Counter(tok for d in docs for tok in set(d))
        self.n_docs = len(docs)
        self.avgdl = (sum(len(d) for d in docs) / len(docs)) if docs else 0.0
        self.vocab = {t: i for i, t in enumerate(sorted(df))}
        self.idf = [0.0] * len(self.vocab)
        for t, i in self.vocab.items():
            self.idf[i] = math.log(1 + (self.n_docs - df[t] + 0.5) / (df[t] + 0.5))
        return self

    def encode_document(self, text: str) -> SparseVector:
        toks = tokenize(text)
        if not toks or not self.vocab:
            return SparseVector()
        tf = Counter(toks)
        dl = len(toks)
        pairs: dict[int, float] = {}
        for t, f in tf.items():
            i = self.vocab.get(t)
            if i is None:
                continue
            pairs[i] = self.idf[i] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1)))
        return _unit(pairs)

    def encode_query(self, text: str) -> SparseVector:
        """Unknown tokens are dropped; a query with no known token yields an empty vector (caller falls back to dense)."""
        pairs = {self.vocab[t]: self.idf[self.vocab[t]] for t in set(tokenize(text)) if t in self.vocab}
        return _unit(pairs)

    def coverage(self, text: str) -> float:
        """Share of the query's content tokens that exist in the corpus vocabulary; 1.0 for an empty query."""
        toks = set(tokenize(text))
        return (sum(1 for t in toks if t in self.vocab) / len(toks)) if toks else 1.0

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"k1": self.k1, "b": self.b, "vocab": self.vocab, "idf": self.idf, "avgdl": self.avgdl, "n_docs": self.n_docs}))

    @classmethod
    def load(cls, path: Path) -> "BM25Encoder":
        d = json.loads(path.read_text())
        enc = cls(d["k1"], d["b"])
        enc.vocab, enc.idf, enc.avgdl, enc.n_docs = d["vocab"], d["idf"], d["avgdl"], d["n_docs"]
        return enc
