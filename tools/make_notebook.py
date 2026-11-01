"""Writes demo.ipynb (kept as a script so the notebook is reproducible and diff-friendly)."""
import json
from pathlib import Path


def md(t): return {"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(keepends=True)}
def py(t): return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": t.strip("\n").splitlines(keepends=True)}


cells = [
    md("""
# Enterprise search RAG demo

Hybrid dense + sparse retrieval over policies, product docs and support FAQs, with cited answers. This notebook runs in
**local mode** with no keys (hash embedder, numpy store, extractive answers). Put `OPENAI_API_KEY` and
`PINECONE_API_KEY` in `.env` and re-run to use OpenAI embeddings, `gpt-4o-mini` answers and a Pinecone index.
"""),
    py("""
import json, os, sys
from pathlib import Path
REPO = Path.cwd() if (Path.cwd() / "rag").exists() else Path.cwd().parent
sys.path.insert(0, str(REPO)); os.chdir(REPO)
from rag.settings import Settings
from rag.pipeline import Pipeline
s = Settings()
print(json.dumps(s.describe(), indent=2))    # names and booleans only, never key values
"""),
    md("## 1. Build the corpus and ingest it"),
    py("""
from tools.make_corpus import write_corpus
print(write_corpus(Path("corpus")))
p = Pipeline(s)
print(json.dumps(p.ingest(), indent=2))
"""),
    md("## 2. Ask, at the three alphas\n\n`alpha=1` dense only, `0` sparse only, `0.5` hybrid. Watch the sources change."),
    py("""
from IPython.display import HTML, display

def show(a):
    cites = "".join(f'<li><b>[{c.n}]</b> {c.title}{" › " + c.heading if c.heading else ""} <i>({c.collection}{", fictional" if c.fictional else ""})</i> — score {c.score} — <a href="{c.url}">{c.url}</a></li>' for c in a.citations)
    others = ", ".join(f"[{x.n}] {x.title} ({x.score})" for x in a.sources if x not in a.citations)
    display(HTML(f"<h4>{a.question} <small>alpha={a.alpha}, {a.generator}</small></h4><p>{a.text}</p><ul>{cites}</ul><p><small>also retrieved: {others or '—'}</small></p>"))

for alpha in (1.0, 0.0, 0.5):
    show(p.ask("What does fullCompanyYlt do and how big is the export?", alpha=alpha))
"""),
    py("""
show(p.ask("working from another country for a month", alpha=0.5, collection="policies"))
show(p.ask("What is the capital of France?"))     # nothing in the corpus: the generator must decline
"""),
    md("## 3. Dense vs sparse vs hybrid on the eval set\n\nRecall@5 and MRR per alpha, overall and per collection. In local mode the hash embedder is lexical, so the paraphrase queries are the expected misses; with OpenAI embeddings those are the ones hybrid should recover."),
    py("""
from rag.evaluate import evaluate, format_table, load_queries
res = evaluate(p.retriever, load_queries(s.eval_path), alphas=(1.0, 0.0, 0.5), k=5)
print(format_table(res))
for r in res:
    print(f"\\nmissed at alpha={r.alpha}: " + ("; ".join(r.misses) or "nothing"))
"""),
    md("## 4. The web UI\n\nRun `python -m rag serve` in a terminal and open http://127.0.0.1:8000 — the same pipeline behind a question box with an alpha slider and clickable citations."),
]
nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
Path("demo.ipynb").write_text(json.dumps(nb, indent=1) + "\n")
print("wrote demo.ipynb")
