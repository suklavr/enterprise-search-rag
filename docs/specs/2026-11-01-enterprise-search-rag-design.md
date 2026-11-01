# Enterprise search RAG demo — design

Date: 2026-11-01. Author: Claude, on Sukla's behalf; Sukla stepped out after the document conversation and asked for the
remaining decisions to be made and the demo to be ready.

## Intent

A small, honest demo of enterprise search over three internal collections — policies, product docs, support FAQs — that
shows **hybrid retrieval** (dense semantic + sparse keyword) beating either one alone, and that **answers with source
citations** a reader can click. The audience is engineers and an engineering VP evaluating whether this pattern is worth
building for real. It must run end to end on a laptop with no API keys (local mode) and switch to Pinecone + OpenAI by
adding two keys to `.env`.

## Goals

1. Ask a question, get a short answer with numbered citations `[1]`, `[2]` that map to passages with title, collection
   and URL.
2. Show the retrieval trade-off with numbers: an eval set scored at dense-only, sparse-only and hybrid, per collection.
3. One code path for local and Pinecone modes: the hybrid maths, chunking and sparse encoding are identical, only the
   vector store and the embedder are swapped.
4. Small enough to read in an hour: ~10 modules, ~15 tests, a CLI, a tiny web page, a notebook.

## Non-goals

- Production hardening: auth, multi-tenancy, rate limits, re-ranking models, streaming.
- Crawling docs.cybcube.com or the internal docs site: both need a browser session we cannot obtain from this
  environment. A crawler module exists for the CMS API but is **unverified** until a `DOCS_API_TOKEN` is supplied.
- Real policies or FAQs: those collections are fabricated and labelled as such in every file and in the README.

## Anti-goals

- Answers that cite nothing or cite passages that were not retrieved. The generator may only use the passages it is
  given, must cite them by number, and must say when the passages do not answer the question.
- Sending internal-only text to OpenAI or Pinecone. The product-docs corpus is derived from CyberCube's public
  documentation digest only; the internal Confluence and repo material from the cat-engine skill is excluded.
- A hybrid score that is secretly one of the two signals. Dense and sparse scores must be on comparable scales so the
  weight `alpha` means what it says.

## The corpus

`corpus/<collection>/<slug>.md`, Markdown with YAML front matter: `id`, `title`, `collection` (`product-docs` |
`policies` | `faqs`), `url` (public page or `internal://…`), `tags`, `fictional: true` where applicable.

- **product-docs** (~12 files): articles written from the docs.cybcube.com digest in the cat-engine skill: model
  overview, event families and scenario classes, frequency / SPoF selection / footprint / impact / severity / financial
  loss modules, model outputs (OEP, AEP, AAL, TCE, SDAL, CV), running a probabilistic analysis, reports, reinsurance
  treaties, platform settings (cost-component mapping), API notes, release notes. Facts come from the digest; nothing
  numeric is invented. Each file links to its real docs.cybcube.com section URL.
- **policies** (12 files, fictional): acceptable use, information security, data classification and handling, access
  requests and offboarding, on-call and incident response, change management, expenses and travel, remote work,
  vendor and third-party risk, secure development, retention and backups, AI tool usage.
- **faqs** (~25 files, fictional, short Q&A about Portfolio Manager, reports, the API, SPoF Intelligence, accounts).

## Retrieval

- **Chunking**: Markdown-aware. Split on headings; within a section, windows of ~350 words with 60-word overlap. Each
  chunk carries `doc_id`, `chunk_id`, `heading_path`, `collection`, `title`, `url`, `text`.
- **Sparse**: a corpus-built BM25 encoder (`k1=1.5`, `b=0.75`): lowercase, keep `[a-z0-9_]+` tokens so identifiers like
  `cat_spofimportancelevelfallback` and `i38` survive, English stop-word list, no stemming. Vocabulary ids are the
  Pinecone sparse indices. Doc vectors hold BM25 term weights, query vectors hold idf per query term; both are
  L2-normalised so sparse dot products sit in `[0, 1]` like cosine. Saved to `data/index/bm25.json`.
- **Dense**: `Embedder` protocol. `OpenAIEmbedder` (`text-embedding-3-small`, 1536-d, batched, unit-normalised) and
  `HashEmbedder` (deterministic 256-d hashed bag of tokens, unit-normalised) for local mode and tests. Hash embeddings
  are lexical, not semantic; the README says so.
- **Hybrid**: convex combination at query time — dense scaled by `alpha`, sparse by `1 − alpha`, score = sum of the two
  dot products. `alpha=1` dense only, `alpha=0` sparse only, default `0.5`. Pinecone computes exactly this with
  `metric="dotproduct"` and `sparse_values`; `LocalStore` computes the same with numpy so results agree in shape and
  ordering logic.
- **Filter**: optional `collection` metadata filter; `top_k` default 5.

## Generation

`Generator` protocol. `OpenAIGenerator` (`gpt-4o-mini`, temperature 0): system prompt says answer only from the numbered
passages, cite every claim as `[n]`, reply "I could not find this in the indexed documents" when nothing fits.
`ExtractiveGenerator` (local): lead sentence(s) of the top passages, each followed by its `[n]`. Both return an
`Answer` with `text`, `citations` (only the `[n]` actually used, in order of first use), `sources` (every retrieved
passage), `alpha`, `mode`.

## Interfaces

- CLI `python -m rag ingest` (rebuild chunks, BM25, embeddings, upsert), `python -m rag ask "q" [--alpha 0.5]
  [--collection faqs] [--top-k 5] [--json]`, `python -m rag eval [--alphas 1,0,0.5]`.
- HTTP `POST /ask {question, alpha?, collection?, top_k?}` → `Answer`; `GET /health` → mode and index size; `GET /`
  serves `static/index.html` (question box, alpha slider with the three presets, collection select, answer with
  citations rendered as links, a sources list with scores).
- `demo.ipynb`: ingest, three asks at the three alphas, the eval table.

## Evaluation

`eval/queries.jsonl`: ~20 queries, each with `expect` (doc ids, any match counts), designed to exercise: exact
identifiers (sparse wins), paraphrased meaning (dense wins), FAQ near-duplicates, vague policy phrasing, and two
questions with no answer in the corpus (the generator must decline). `python -m rag eval` prints recall@5 and MRR for
each alpha, overall and per collection.

## Settings and modes

`rag/settings.py` (pydantic-settings, `.env`): `OPENAI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX=enterprise-search`,
`PINECONE_CLOUD=aws`, `PINECONE_REGION=us-east-1`, `EMBED_MODEL`, `CHAT_MODEL`, `DOCS_API_TOKEN` (crawler only),
`RAG_MODE=auto|local|pinecone`. `auto` = pinecone when both keys are set, else local. Local index persists under
`data/index/` (git-ignored). Secrets are never logged or printed.

## Left to the builder

File layout under `rag/`, exact prompt wording, the HTML page's styling, and the notebook's cell split. Tests use the
local store and the hash embedder; the Pinecone store is tested against a fake client that records upsert and query
payloads (sparse indices are ints, values are floats, scaling applied).
