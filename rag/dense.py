"""Dense (semantic) side of hybrid search. `OpenAIEmbedder` is the real thing; `HashEmbedder` is a deterministic hashed
bag-of-tokens (unsigned, so cosines are in [0, 1]) so the whole pipeline (and the tests) run with no key. Hash embeddings are lexical, not semantic — they
make the plumbing demonstrable, not the quality. All vectors are unit length so the dot product is the cosine."""
from __future__ import annotations

import hashlib
import math
from typing import Protocol

from rag.sparse import tokenize


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def unit(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm else vec


class HashEmbedder:
    name = "hash"

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _slot(self, token: str) -> int:
        # unsigned counts: every coordinate is >= 0, so the cosine between two texts is in [0, 1] and never negative
        return int.from_bytes(hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()[:4], "big") % self.dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            toks = tokenize(text)
            for t in toks:
                vec[self._slot(t)] += 1.0
            for a, b in zip(toks, toks[1:]):              # bigrams give a little phrase sensitivity
                vec[self._slot(f"{a}_{b}")] += 0.5
            out.append(unit(vec))
        return out


class OpenAIEmbedder:
    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dim: int = 1536, batch_size: int = 100, client=None):
        from openai import OpenAI
        self.name, self.dim, self.batch_size = model, dim, batch_size
        self._client = client or OpenAI(api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = [t.replace("\n", " ") for t in texts[start:start + self.batch_size]]
            resp = self._client.embeddings.create(model=self.name, input=batch, dimensions=self.dim)
            out.extend(unit(list(d.embedding)) for d in sorted(resp.data, key=lambda d: d.index))
        return out
