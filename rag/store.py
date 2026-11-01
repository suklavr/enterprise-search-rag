"""Vector stores. Both compute the same hybrid score:

    score = alpha * <dense_doc, dense_query> + (1 - alpha) * <sparse_doc, sparse_query>

`LocalStore` does it with numpy and persists to `data/index/`; `PineconeStore` lets Pinecone do it by scaling the
query's dense values by `alpha` and sparse values by `1 - alpha` on an index with `metric="dotproduct"`. Sparse weights
are non-negative and unit-normalised, so that term is in [0, 1]; dense vectors are unit length, so that term is a cosine
in [-1, 1] — [0, 1] for the hash embedder (unsigned counts) and in practice for OpenAI embeddings. The local store
clamps a negative cosine to 0. Both terms are bounded, which is what makes `alpha` meaningful; it does not make the
two score distributions identical, so compare alphas with the eval rather than by eye."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from rag.chunking import Chunk
from rag.sparse import SparseVector

EPS = 1e-6     # Pinecone rejects an all-zero dense vector; alpha=0 is sent as this instead


@dataclass
class Hit:
    chunk: Chunk
    score: float
    dense: float | None = None      # the two components, when the store can report them (local only)
    sparse: float | None = None


class VectorStore(Protocol):
    name: str

    def reset(self, dim: int) -> None: ...
    def upsert(self, chunks: list[Chunk], dense: list[list[float]], sparse: list[SparseVector]) -> None: ...
    def query(self, dense: list[float], sparse: SparseVector, alpha: float, top_k: int, collection: str | None = None) -> list[Hit]: ...
    def count(self) -> int: ...


def clamp_alpha(alpha: float) -> float:
    return min(1.0, max(0.0, float(alpha)))


class LocalStore:
    name = "local"

    def __init__(self, index_dir: Path | None = None):
        self.index_dir = Path(index_dir) if index_dir else None
        self.chunks: list[Chunk] = []
        self.dense = np.zeros((0, 0), dtype=np.float32)
        self.sparse: list[dict[int, float]] = []
        self.dim = 0

    def reset(self, dim: int) -> None:
        self.chunks, self.sparse, self.dim = [], [], dim
        self.dense = np.zeros((0, dim), dtype=np.float32)

    def upsert(self, chunks: list[Chunk], dense: list[list[float]], sparse: list[SparseVector]) -> None:
        assert len(chunks) == len(dense) == len(sparse)
        existing = {c.id: i for i, c in enumerate(self.chunks)}
        rows = []
        for c, d, s in zip(chunks, dense, sparse):
            if c.id in existing:
                i = existing[c.id]
                self.chunks[i], self.sparse[i] = c, s.as_dict()
                self.dense[i] = np.asarray(d, dtype=np.float32)
            else:
                self.chunks.append(c); self.sparse.append(s.as_dict()); rows.append(d)
        if rows:
            self.dense = np.vstack([self.dense, np.asarray(rows, dtype=np.float32)]) if self.dense.size else np.asarray(rows, dtype=np.float32)
            self.dim = self.dense.shape[1]

    def query(self, dense: list[float], sparse: SparseVector, alpha: float, top_k: int, collection: str | None = None) -> list[Hit]:
        if not self.chunks:
            return []
        alpha = clamp_alpha(alpha)
        if alpha > 0 and len(dense) != self.dim:
            raise RuntimeError(f"index was built with {self.dim}-d embeddings but the query has {len(dense)}; run `python -m rag ingest`")
        ds = np.maximum(self.dense @ np.asarray(dense, dtype=np.float32), 0.0) if alpha > 0 else np.zeros(len(self.chunks), dtype=np.float32)
        if alpha == 0 and len(dense) == self.dim:
            ds = np.maximum(self.dense @ np.asarray(dense, dtype=np.float32), 0.0)      # still reported as evidence, just not blended
        q = sparse.as_dict()
        ss = np.asarray([sum(w * q[i] for i, w in row.items() if i in q) for row in self.sparse], dtype=np.float32) if q else np.zeros(len(self.chunks), dtype=np.float32)
        score = alpha * ds + (1 - alpha) * ss
        order = [i for i in np.argsort(-score, kind="stable") if score[i] > 0 and (collection is None or self.chunks[i].collection == collection)]
        return [Hit(self.chunks[i], float(score[i]), float(ds[i]), float(ss[i])) for i in order[:top_k]]      # score 0 = no evidence at all: not a hit

    def count(self) -> int:
        return len(self.chunks)

    def save(self, index_dir: Path | None = None, meta: dict | None = None) -> Path:
        d = Path(index_dir or self.index_dir)
        d.mkdir(parents=True, exist_ok=True)
        (d / "meta.json").write_text(json.dumps({"dim": self.dim, "chunks": len(self.chunks), **(meta or {})}))
        np.save(d / "dense.npy", self.dense)
        (d / "chunks.json").write_text(json.dumps([{"id": c.id, **c.to_metadata()} for c in self.chunks]))
        (d / "sparse.json").write_text(json.dumps([[[i, v] for i, v in row.items()] for row in self.sparse]))
        return d

    @classmethod
    def load(cls, index_dir: Path) -> "LocalStore":
        d = Path(index_dir)
        st = cls(d)
        st.dense = np.load(d / "dense.npy")
        st.dim = st.dense.shape[1] if st.dense.ndim == 2 else 0
        st.chunks = [Chunk.from_metadata(m.pop("id"), m) for m in json.loads((d / "chunks.json").read_text())]
        st.sparse = [{int(i): float(v) for i, v in row} for row in json.loads((d / "sparse.json").read_text())]
        return st

    @classmethod
    def exists(cls, index_dir: Path) -> bool:
        return (Path(index_dir) / "dense.npy").exists()

    @classmethod
    def meta(cls, index_dir: Path) -> dict:
        p = Path(index_dir) / "meta.json"
        return json.loads(p.read_text()) if p.exists() else {}


class PineconeStore:
    """Serverless index, dotproduct metric, one namespace. `client` is a `pinecone.Pinecone`-like object; tests pass a fake."""
    name = "pinecone"

    def __init__(self, api_key: str | None, index_name: str, cloud: str = "aws", region: str = "us-east-1", namespace: str = "demo", client=None, batch_size: int = 100):
        if client is None:
            from pinecone import Pinecone
            client = Pinecone(api_key=api_key)
        self._pc, self.index_name, self.cloud, self.region, self.namespace, self.batch_size = client, index_name, cloud, region, namespace, batch_size
        self._index = None

    @staticmethod
    def _field(obj, name, default=None):
        return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)

    def _ensure(self, dim: int | None = None):
        if self._index is None:
            names = {self._field(i, "name", i) for i in self._pc.list_indexes()}
            if self.index_name not in names:
                if dim is None:
                    raise RuntimeError(f"Pinecone index {self.index_name!r} does not exist; run ingest first")
                from pinecone import ServerlessSpec
                self._pc.create_index(name=self.index_name, dimension=dim, metric="dotproduct", spec=ServerlessSpec(cloud=self.cloud, region=self.region))
                for _ in range(60):
                    if self._field(self._field(self._pc.describe_index(self.index_name), "status", {}), "ready"):
                        break
                    time.sleep(2)
            else:
                desc = self._pc.describe_index(self.index_name)
                have_dim, metric = self._field(desc, "dimension"), str(self._field(desc, "metric", "") or "").lower()
                if dim is not None and have_dim not in (None, dim):
                    raise RuntimeError(f"Pinecone index {self.index_name!r} has dimension {have_dim}, the embedder produces {dim}: "
                                       "set PINECONE_INDEX to a new name or delete the index")
                if metric and metric != "dotproduct":
                    raise RuntimeError(f"Pinecone index {self.index_name!r} uses metric {metric!r}; hybrid search needs 'dotproduct'")
            self._index = self._pc.Index(self.index_name)
        return self._index

    def reset(self, dim: int) -> None:
        idx = self._ensure(dim)
        try:
            idx.delete(delete_all=True, namespace=self.namespace)
        except Exception as err:        # noqa: BLE001 - only "nothing to delete" is fine; auth or server errors must surface
            if type(err).__name__ not in ("NotFoundException", "NotFoundError") and "404" not in str(err) and "not found" not in str(err).lower():
                raise

    def upsert(self, chunks: list[Chunk], dense: list[list[float]], sparse: list[SparseVector]) -> None:
        idx = self._ensure(len(dense[0]) if dense else None)
        vectors = []
        for c, d, s in zip(chunks, dense, sparse):
            v = {"id": c.id, "values": [float(x) for x in d], "metadata": c.to_metadata()}
            if s:
                v["sparse_values"] = {"indices": [int(i) for i in s.indices], "values": [float(x) for x in s.values]}
            vectors.append(v)
        for start in range(0, len(vectors), self.batch_size):
            idx.upsert(vectors=vectors[start:start + self.batch_size], namespace=self.namespace)

    def query(self, dense: list[float], sparse: SparseVector, alpha: float, top_k: int, collection: str | None = None) -> list[Hit]:
        alpha = clamp_alpha(alpha)
        scale = alpha if alpha > 0 else EPS
        kwargs = {"vector": [float(x) * scale for x in dense], "top_k": top_k, "include_metadata": True, "namespace": self.namespace}
        if sparse and alpha < 1:
            kwargs["sparse_vector"] = {"indices": [int(i) for i in sparse.indices], "values": [float(v) * (1 - alpha) for v in sparse.values]}
        if collection:
            kwargs["filter"] = {"collection": {"$eq": collection}}
        res = self._ensure().query(**kwargs)
        matches = res.get("matches", []) if isinstance(res, dict) else getattr(res, "matches", [])
        out = []
        for m in matches:
            mid = m["id"] if isinstance(m, dict) else m.id
            meta = (m.get("metadata") if isinstance(m, dict) else m.metadata) or {}
            score = float(m["score"] if isinstance(m, dict) else m.score)
            out.append(Hit(Chunk.from_metadata(mid, meta), score))
        return out

    def count(self) -> int:
        stats = self._ensure().describe_index_stats()
        ns = stats.get("namespaces", {}) if isinstance(stats, dict) else getattr(stats, "namespaces", {}) or {}
        n = ns.get(self.namespace)
        return int((n.get("vector_count") if isinstance(n, dict) else getattr(n, "vector_count", 0)) or 0) if n else 0
