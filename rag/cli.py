"""`python -m rag ingest | ask | eval | serve`."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from rag.documents import load_corpus
from rag.evaluate import evaluate, format_table, load_queries
from rag.pipeline import Pipeline
from rag.settings import Settings


def _print_answer(a) -> None:
    print(a.text)
    if a.citations:
        print("\nSources:")
        for c in a.citations:
            tag = " (fictional demo content)" if c.fictional else ""
            where = f" › {c.heading}" if c.heading else ""
            print(f"  [{c.n}] {c.title}{where} — {c.collection}{tag}\n      {c.url}  (score {c.score})")
    others = [s for s in a.sources if s not in a.citations]
    if others:
        print("\nAlso retrieved: " + ", ".join(f"[{s.n}] {s.title} ({s.score})" for s in others))
    print(f"\nalpha={a.alpha} · store={a.mode} · generator={a.generator}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m rag", description="Hybrid enterprise search RAG demo")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest", help="chunk the corpus, fit BM25, embed, upsert into the store")
    ask = sub.add_parser("ask", help="ask a question")
    ask.add_argument("question")
    ask.add_argument("--alpha", type=float, default=None, help="1.0 dense only, 0.0 sparse only, 0.5 hybrid (default)")
    ask.add_argument("--collection", choices=["product-docs", "policies", "faqs"], default=None)
    ask.add_argument("--top-k", type=int, default=None)
    ask.add_argument("--json", action="store_true")
    ev = sub.add_parser("eval", help="recall@k and MRR at several alphas")
    ev.add_argument("--alphas", default="1,0,0.5")
    ev.add_argument("--k", type=int, default=5)
    ev.add_argument("--misses", action="store_true", help="list the queries each alpha missed")
    srv = sub.add_parser("serve", help="run the web UI and API")
    srv.add_argument("--port", type=int, default=8000)
    srv.add_argument("--host", default="127.0.0.1")
    sub.add_parser("info", help="which store, embedder and generator are configured (no secrets)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    s = Settings()
    if args.cmd == "info":
        print(json.dumps(s.describe(), indent=2)); return 0
    if args.cmd == "serve":
        import uvicorn
        from rag.api import create_app
        uvicorn.run(create_app(s), host=args.host, port=args.port); return 0
    p = Pipeline(s)
    if args.cmd == "ingest":
        print(json.dumps(p.ingest(), indent=2)); return 0
    if args.cmd == "ask":
        a = p.ask(args.question, alpha=args.alpha, top_k=args.top_k, collection=args.collection)
        print(json.dumps(asdict(a), indent=2)) if args.json else _print_answer(a)
        return 0
    if args.cmd == "eval":
        alphas = tuple(float(x) for x in args.alphas.split(","))
        collection_of = {d.id: d.collection for d in load_corpus(s.corpus_dir)} if Path(s.corpus_dir).exists() else {}
        res = evaluate(p.retriever, load_queries(s.eval_path), alphas=alphas, k=args.k, collection_of=collection_of,
                       ask=lambda q, a, c: p.ask(q, alpha=a, collection=c).text)
        print(format_table(res, args.k))
        if args.misses:
            for r in res:
                print(f"\nmissed at alpha={r.alpha}: " + ("; ".join(r.misses) or "nothing") + (f" | answered although unanswerable: {'; '.join(r.false_answers)}" if r.false_answers else ""))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
