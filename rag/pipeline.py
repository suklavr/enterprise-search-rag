"""Wires the pieces: corpus → chunks → BM25 + embeddings → store; question → hybrid retrieval → cited answer."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from rag.chunking import Chunk, chunk_corpus
from rag.dense import Embedder, HashEmbedder, OpenAIEmbedder
from rag.documents import load_corpus
from rag.generate import NOT_FOUND, Answer, Citation, ExtractiveGenerator, Generator, OpenAIGenerator, cited_numbers, snippet
from rag.settings import Settings
from rag.sparse import BM25Encoder
from rag.store import Hit, LocalStore, PineconeStore, VectorStore, clamp_alpha

log = logging.getLogger("rag")


def build_embedder(s: Settings) -> Embedder:
    return OpenAIEmbedder(s.openai_key(), s.embed_model, s.embed_dim) if s.openai_enabled else HashEmbedder()


def build_generator(s: Settings) -> Generator:
    return OpenAIGenerator(s.openai_key(), s.chat_model) if s.openai_enabled else ExtractiveGenerator()


def build_store(s: Settings) -> VectorStore:
    if s.store_mode == "pinecone":
        return PineconeStore(s.pinecone_key(), s.pinecone_index, s.pinecone_cloud, s.pinecone_region, s.pinecone_namespace)
    return LocalStore.load(s.index_dir) if LocalStore.exists(s.index_dir) else LocalStore(s.index_dir)


@dataclass
class Retriever:
    embedder: Embedder
    bm25: BM25Encoder
    store: VectorStore

    def search(self, question: str, alpha: float = 0.5, top_k: int = 5, collection: str | None = None) -> list[Hit]:
        dense = self.embedder.embed([question])[0]
        sparse = self.bm25.encode_query(question)
        return self.store.query(dense, sparse, alpha, top_k, collection)


class Pipeline:
    def __init__(self, settings: Settings, embedder: Embedder | None = None, generator: Generator | None = None, store: VectorStore | None = None, bm25: BM25Encoder | None = None):
        self.s = settings
        self.embedder = embedder or build_embedder(settings)
        self.generator = generator or build_generator(settings)
        self.store = store or build_store(settings)
        self.bm25 = bm25 or (BM25Encoder.load(self.bm25_path) if self.bm25_path.exists() else BM25Encoder())
        self.index_warning: str | None = None
        if isinstance(self.store, LocalStore) and self.store.count():
            meta = LocalStore.meta(self.s.index_dir)
            if meta and (meta.get("embedder") != self.embedder.name or meta.get("dim") != self.embedder.dim):
                self.index_warning = f"local index was built with embedder {meta.get('embedder')!r} ({meta.get('dim')}-d); the current one is {self.embedder.name!r} ({self.embedder.dim}-d): run `python -m rag ingest`"

    @property
    def bm25_path(self) -> Path:
        return Path(self.s.index_dir) / "bm25.json"

    @property
    def mode(self) -> str:
        return self.store.name

    @property
    def retriever(self) -> Retriever:
        return Retriever(self.embedder, self.bm25, self.store)

    def ingest(self, corpus_dir: Path | None = None) -> dict:
        docs = load_corpus(corpus_dir or self.s.corpus_dir)
        chunks = chunk_corpus(docs, self.s.chunk_words, self.s.chunk_overlap)
        if not chunks:
            raise ValueError("no documents found to ingest")
        self.bm25 = BM25Encoder().fit([c.text for c in chunks])
        dense = self.embedder.embed([c.text for c in chunks])
        sparse = [self.bm25.encode_document(c.text) for c in chunks]
        self.store.reset(len(dense[0]))
        self.store.upsert(chunks, dense, sparse)
        if isinstance(self.store, LocalStore):
            self.store.save(self.s.index_dir, meta={"embedder": self.embedder.name, "store": self.store.name})
        self.bm25.save(self.bm25_path)          # written last: the vocabulary on disk always matches what the store holds
        self.index_warning = None
        by = {}
        for c in chunks:
            by[c.collection] = by.get(c.collection, 0) + 1
        log.info("ingested %d docs, %d chunks into %s", len(docs), len(chunks), self.store.name)
        return {"documents": len(docs), "chunks": len(chunks), "by_collection": by, "store": self.store.name, "embedder": self.embedder.name, "vocab": len(self.bm25.vocab)}

    def ask(self, question: str, alpha: float | None = None, top_k: int | None = None, collection: str | None = None) -> Answer:
        alpha = clamp_alpha(self.s.default_alpha if alpha is None else alpha)
        top_k = top_k or self.s.default_top_k
        if not self.bm25.vocab or self.store.count() == 0:
            raise RuntimeError("no index yet: run `python -m rag ingest` first")
        if self.index_warning:
            raise RuntimeError(self.index_warning)
        hits = self.retriever.search(question, alpha, top_k, collection)
        text = self.generator.generate(question, hits, coverage=self.bm25.coverage(question))
        sources = [Citation(n=i + 1, chunk_id=h.chunk.id, doc_id=h.chunk.doc_id, title=h.chunk.title, collection=h.chunk.collection, url=h.chunk.url,
                            heading=h.chunk.heading, snippet=snippet(h.chunk.text), score=round(h.score, 4), fictional=h.chunk.fictional) for i, h in enumerate(hits)]
        used = cited_numbers(text, len(sources))
        found = text.strip() != NOT_FOUND and bool(used)
        return Answer(question=question, text=text, citations=[sources[n - 1] for n in used], sources=sources, alpha=alpha, mode=self.mode,
                      generator=self.generator.name, found=found)
