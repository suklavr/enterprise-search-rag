import json
from pathlib import Path

from fastapi.testclient import TestClient

from rag.api import create_app
from rag.cli import main
from rag.pipeline import Pipeline
from rag.settings import Settings
from tests.test_store_and_pipeline import _corpus


def _settings(tmp_path: Path) -> Settings:
    return Settings(_env_file=None, rag_mode="local", corpus_dir=_corpus(tmp_path), index_dir=tmp_path / "index", static_dir=tmp_path / "static", eval_path=tmp_path / "q.jsonl")


def test_cli_ingest_ask_eval_and_info(tmp_path: Path, monkeypatch, capsys):
    s = _settings(tmp_path)
    monkeypatch.setattr("rag.cli.Settings", lambda: s)
    assert main(["info"]) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["store"] == "local" and info["openai_key"] is False and "api_key" not in json.dumps(info)
    assert main(["ingest"]) == 0 and json.loads(capsys.readouterr().out)["chunks"] == 3
    assert main(["ask", "Cat_SpofImportanceLevelFallback", "--alpha", "0", "--json"]) == 0
    a = json.loads(capsys.readouterr().out)
    assert a["citations"][0]["doc_id"] == "doc-footprint"
    assert main(["ask", "conference reimbursement", "--collection", "policies"]) == 0
    out = capsys.readouterr().out
    assert "Sources:" in out and "Expenses policy" in out and "fictional demo content" in out and "alpha=0.5" in out
    (tmp_path / "q.jsonl").write_text('{"q": "download loss metrics report", "expect": ["faq-download"], "collection": "faqs"}\n# comment\n{"q": "sky colour", "expect": []}\n')
    assert main(["eval", "--alphas", "0,0.5", "--misses"]) == 0
    out = capsys.readouterr().out
    assert "sparse only" in out and "faqs: 1.00/1.00" in out and "missed at alpha=0.0: nothing" in out


def test_api_health_ask_and_index_page(tmp_path: Path):
    s = _settings(tmp_path)
    p = Pipeline(s)
    c = TestClient(create_app(s, pipeline=p))
    assert c.post("/ask", json={"question": "anything"}).status_code == 409           # not ingested yet
    p.ingest()
    h = c.get("/health").json()
    assert h["status"] == "ok" and h["chunks"] == 3 and h["store"] == "local" and "pinecone_api_key" not in h
    r = c.post("/ask", json={"question": "default importance level", "alpha": 0.0, "top_k": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["citations"][0]["doc_id"] == "doc-footprint" and 1 <= len(body["sources"]) <= 2 and body["alpha"] == 0.0
    assert c.post("/ask", json={"question": "x", "collection": "nope"}).status_code == 422
    assert c.post("/ask", json={"question": "", "alpha": 0.5}).status_code == 422
    assert c.get("/").status_code == 404                                              # no static page in this temp dir
    (tmp_path / "static").mkdir(); (tmp_path / "static" / "index.html").write_text("<html>ui</html>")
    assert c.get("/").text == "<html>ui</html>"


def test_api_reloads_after_reingest_and_maps_unexpected_errors_to_502(tmp_path: Path, monkeypatch):
    import time
    s = _settings(tmp_path)
    Pipeline(s).ingest()
    c = TestClient(create_app(s))
    assert c.get("/health").json()["chunks"] == 3
    (tmp_path / "corpus" / "faqs" / "extra.md").write_text("---\nid: faq-extra\ntitle: Extra FAQ about treaty tags\nfictional: true\n---\nTreaty tags are separated by semicolons.")
    time.sleep(0.01)
    Pipeline(s).ingest()                                                   # a separate process re-ingests while the server runs
    assert c.get("/health").json()["chunks"] == 4
    assert c.post("/ask", json={"question": "treaty tags semicolons", "alpha": 0.0}).json()["citations"][0]["doc_id"] == "faq-extra"
    # an SDK-style failure must not leak as a 500 traceback
    class Boom:
        name = "boom"
        def generate(self, question, hits, coverage=1.0):
            raise ValueError("Incorrect API key provided: sk-abc...xyz")
    p = Pipeline(s, generator=Boom())
    c2 = TestClient(create_app(s, pipeline=p), raise_server_exceptions=False)
    r = c2.post("/ask", json={"question": "treaty tags"})
    assert r.status_code == 502 and "sk-abc" not in r.text and "ValueError" in r.json()["detail"]
