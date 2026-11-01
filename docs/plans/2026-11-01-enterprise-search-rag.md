# Enterprise search RAG demo — implementation plan

> Executed inline (superpowers:executing-plans) on 2026-11-01 while the owner was away; final whole-branch review by a
> fresh reviewer, then one fix pass.

**Goal:** a laptop-runnable hybrid-search RAG demo over three collections with cited answers and a dense/sparse/hybrid
eval, in local mode by default and Pinecone + OpenAI mode when keys exist.

**Spec:** docs/specs/2026-11-01-enterprise-search-rag-design.md

## Global constraints

- Python 3.11+, pydantic v2, numpy, openai, pinecone; no other runtime deps. Tests never need network or keys.
- Secrets only via `.env`; never printed or logged. `.env` git-ignored; `.env.example` committed.
- Dense and sparse scores both in `[0, 1]`; hybrid = `alpha*dense + (1-alpha)*sparse` in both stores.

## Review focus

1. A query whose tokens are all unknown to the BM25 vocabulary: sparse vector empty, hybrid falls back to dense without error.
2. `alpha=0` and `alpha=1` on the Pinecone store: no all-zero dense vector sent, no empty sparse vector sent.
3. A document with no headings and a document shorter than one window: exactly one chunk each, heading path empty.
4. The generator cites a number outside the retrieved range: citation list ignores it rather than crashing.
5. Eval query with a collection filter whose expected doc lives elsewhere: recall 0, no exception.

## Tasks

1. Skeleton + settings + documents + chunking + sparse + dense (tests: front matter, chunk windows and overlap, BM25
   idf/normalisation/unknown tokens, hash embedder determinism and unit norm).
2. Stores: LocalStore (save/load, alpha extremes order by the right signal, collection filter) and PineconeStore against a
   fake client (payload shape, scaling, alpha extremes).
3. Generation + pipeline + eval (extractive generator cites retrieved numbers, OpenAI generator prompt contains numbered
   passages and the not-found rule, cited_numbers parsing, pipeline ingest→ask round trip in local mode, eval metrics).
4. CLI + API + static page (ask/ingest/eval subcommands; /ask, /health with TestClient).
5. Corpus (product-docs from the public digest, fictional policies and FAQs), eval queries, README, notebook, .env.example;
   full run of ingest + eval + a few asks in local mode.
6. Commit; dispatch review; fix pass; sleep.
