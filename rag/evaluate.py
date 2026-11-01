"""Retrieval evaluation: recall@k and MRR per alpha (dense-only 1.0, sparse-only 0.0, hybrid 0.5 by default), overall
and per collection of the EXPECTED document, plus a decline rate on the queries the corpus cannot answer.

A query hits when any retrieved chunk belongs to one of its expected documents. Queries with an empty `expect` are the
"must decline" set: they are not scored for recall; instead the generator is asked and a decline is counted."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from rag.generate import NOT_FOUND
from rag.pipeline import Retriever


@dataclass
class EvalQuery:
    q: str
    expect: list[str]                 # document ids; empty = the corpus has no answer (scored as a decline, not recall)
    collection: str | None = None     # optional retrieval filter
    note: str = ""


@dataclass
class EvalResult:
    alpha: float
    n: int
    recall: float
    mrr: float
    by_collection: dict[str, dict[str, float]] = field(default_factory=dict)
    misses: list[str] = field(default_factory=list)
    declines: int = 0                 # how many of the no-answer queries the generator declined
    declines_total: int = 0
    false_answers: list[str] = field(default_factory=list)


def load_queries(path: Path) -> list[EvalQuery]:
    out = []
    for line in Path(path).read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            d = json.loads(line)
            out.append(EvalQuery(q=d["q"], expect=list(d.get("expect", [])), collection=d.get("collection"), note=d.get("note", "")))
    return out


def evaluate(retriever: Retriever, queries: list[EvalQuery], alphas: tuple[float, ...] = (1.0, 0.0, 0.5), k: int = 5,
             collection_of: dict[str, str] | None = None, ask: Callable[[str, float, str | None], str] | None = None) -> list[EvalResult]:
    """`collection_of` maps document id -> collection so rows group by where the answer lives, not by the filter used.
    `ask(question, alpha, collection) -> answer text` enables the decline column."""
    collection_of = collection_of or {}
    results = []
    for alpha in alphas:
        scored = [q for q in queries if q.expect]
        unanswerable = [q for q in queries if not q.expect]
        hits_n, rr = 0, 0.0
        per: dict[str, list[tuple[int, float]]] = {}
        misses = []
        for q in scored:
            hits = retriever.search(q.q, alpha=alpha, top_k=k, collection=q.collection)
            rank = next((i + 1 for i, h in enumerate(hits) if h.chunk.doc_id in q.expect), None)
            hit = 1 if rank else 0
            hits_n += hit
            rr += (1 / rank) if rank else 0.0
            group = collection_of.get(q.expect[0]) or q.collection or "unknown"
            per.setdefault(group, []).append((hit, (1 / rank) if rank else 0.0))
            if not rank:
                misses.append(q.q)
        declined, false_answers = 0, []
        if ask is not None:
            for q in unanswerable:
                if ask(q.q, alpha, q.collection).strip() == NOT_FOUND:
                    declined += 1
                else:
                    false_answers.append(q.q)
        n = len(scored)
        results.append(EvalResult(alpha=alpha, n=n, recall=round(hits_n / n, 3) if n else 0.0, mrr=round(rr / n, 3) if n else 0.0,
                                  by_collection={c: {"n": len(v), "recall": round(sum(h for h, _ in v) / len(v), 3), "mrr": round(sum(r for _, r in v) / len(v), 3)} for c, v in per.items()},
                                  misses=misses, declines=declined, declines_total=len(unanswerable) if ask is not None else 0, false_answers=false_answers))
    return results


def format_table(results: list[EvalResult], k: int = 5) -> str:
    label = {1.0: "dense only", 0.0: "sparse only"}
    lines = [f"{'alpha':>6}  {'mode':<12}{'recall@' + str(k):>10}{'MRR':>8}{'declines':>10}   per collection of the expected document (recall/MRR)"]
    for r in results:
        per = "  ".join(f"{c}: {v['recall']:.2f}/{v['mrr']:.2f}" for c, v in sorted(r.by_collection.items()))
        dec = f"{r.declines}/{r.declines_total}" if r.declines_total else "n/a"
        lines.append(f"{r.alpha:>6.2f}  {label.get(r.alpha, 'hybrid'):<12}{r.recall:>10.3f}{r.mrr:>8.3f}{dec:>10}   {per}")
    return "\n".join(lines)
