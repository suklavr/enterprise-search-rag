import math
from pathlib import Path

import pytest

from rag.chunking import Chunk
from rag.dense import HashEmbedder
from rag.evaluate import EvalQuery, evaluate, format_table
from rag.generate import NOT_FOUND, ExtractiveGenerator, OpenAIGenerator, cited_numbers, passages_block
from rag.pipeline import Pipeline, Retriever
from rag.settings import Settings
from rag.sparse import BM25Encoder, SparseVector
from rag.store import EPS, Hit, LocalStore, PineconeStore


def chunk(i, text, collection="faqs", doc=None):
    return Chunk(id=f"{doc or 'd' + str(i)}#0", doc_id=doc or f"d{i}", title=f"Doc {i}", collection=collection, url=f"u{i}", heading_path=[], text=text, position=0)


def test_local_store_alpha_extremes_follow_the_right_signal_and_filter(tmp_path: Path):
    st = LocalStore(tmp_path)
    st.reset(2)
    # dense says chunk A, sparse says chunk B
    chunks = [chunk(1, "A", "faqs"), chunk(2, "B", "policies")]
    st.upsert(chunks, [[1.0, 0.0], [0.0, 1.0]], [SparseVector([7], [1.0]), SparseVector([9], [1.0])])
    q_dense, q_sparse = [1.0, 0.0], SparseVector([9], [1.0])
    assert [h.chunk.doc_id for h in st.query(q_dense, q_sparse, alpha=1.0, top_k=2)] == ["d1"]          # d2 has no dense evidence: score 0 is not a hit
    assert [h.chunk.doc_id for h in st.query(q_dense, q_sparse, alpha=0.0, top_k=2)] == ["d2"]
    hy = st.query(q_dense, q_sparse, alpha=0.5, top_k=2)
    assert math.isclose(hy[0].score, 0.5) and math.isclose(hy[1].score, 0.5) and hy[0].dense is not None
    assert [h.chunk.doc_id for h in st.query(q_dense, q_sparse, 0.5, 5, collection="policies")] == ["d2"]
    assert st.query(q_dense, SparseVector(), alpha=0.0, top_k=2) == []                     # no known query tokens: no hits, no crash
    st.upsert([chunk(3, "neg", "faqs")], [[-1.0, 0.0]], [SparseVector()])
    assert all(h.dense >= 0 for h in st.query(q_dense, q_sparse, alpha=0.5, top_k=5))         # negative cosine clamped to 0
    st.upsert([chunk(1, "A2", "faqs")], [[0.0, 1.0]], [SparseVector([7], [1.0])])          # re-upsert replaces, count unchanged
    assert st.count() == 3 and st.chunks[0].text == "A2"
    st.save()
    back = LocalStore.load(tmp_path)
    assert back.count() == 3 and back.sparse[1] == {9: 1.0} and back.chunks[1].collection == "policies" and LocalStore.exists(tmp_path)


class FakeIndex:
    def __init__(self):
        self.upserts, self.queries, self.deleted = [], [], []
        self.matches = [{"id": "d9#0", "score": 0.7, "metadata": {"doc_id": "d9", "title": "T", "collection": "faqs", "url": "u", "heading": "", "position": 0, "text": "T\nbody"}}]

    def upsert(self, vectors, namespace):
        self.upserts.append((namespace, vectors))

    def query(self, **kw):
        self.queries.append(kw)
        return {"matches": self.matches}

    def delete(self, delete_all, namespace):
        self.deleted.append(namespace)

    def describe_index_stats(self):
        return {"namespaces": {"demo": {"vector_count": 3}}}


class FakePinecone:
    def __init__(self, existing=("enterprise-search",)):
        self.index = FakeIndex()
        self.created = []
        self._names = list(existing)

    def list_indexes(self):
        return [{"name": n} for n in self._names] and [type("I", (), {"name": n})() for n in self._names]

    def create_index(self, name, dimension, metric, spec):
        self.created.append((name, dimension, metric)); self._names.append(name)

    def describe_index(self, name):
        return type("D", (), {"status": {"ready": True}})()

    def Index(self, name):
        return self.index


def test_pinecone_store_payloads_and_alpha_extremes():
    pc = FakePinecone(existing=())
    st = PineconeStore(None, "enterprise-search", client=pc, batch_size=2)
    st.reset(3)
    assert pc.created == [("enterprise-search", 3, "dotproduct")] and pc.index.deleted == ["demo"]
    chunks = [chunk(i, f"t{i}") for i in range(3)]
    st.upsert(chunks, [[0.6, 0.8, 0.0]] * 3, [SparseVector([4, 10], [0.6, 0.8]), SparseVector(), SparseVector([1], [1.0])])
    assert [len(v) for _, v in pc.index.upserts] == [2, 1]
    v0, v1 = pc.index.upserts[0][1]
    assert v0["sparse_values"] == {"indices": [4, 10], "values": [0.6, 0.8]} and "sparse_values" not in v1 and v0["metadata"]["collection"] == "faqs"
    assert all(isinstance(i, int) for i in v0["sparse_values"]["indices"])
    hits = st.query([1.0, 0.0, 0.0], SparseVector([4], [1.0]), alpha=0.25, top_k=5, collection="faqs")
    q = pc.index.queries[-1]
    assert q["vector"] == [0.25, 0.0, 0.0] and q["sparse_vector"] == {"indices": [4], "values": [0.75]} and q["filter"] == {"collection": {"$eq": "faqs"}}
    assert hits[0].chunk.doc_id == "d9" and hits[0].score == 0.7 and hits[0].dense is None
    st.query([1.0, 0.0, 0.0], SparseVector([4], [1.0]), alpha=1.0, top_k=5)
    assert "sparse_vector" not in pc.index.queries[-1]                                   # dense only: no sparse payload
    st.query([1.0, 0.0, 0.0], SparseVector([4], [1.0]), alpha=0.0, top_k=5)
    assert pc.index.queries[-1]["vector"] == [EPS, 0.0, 0.0] and pc.index.queries[-1]["sparse_vector"]["values"] == [1.0]   # never an all-zero dense vector
    st.query([1.0, 0.0, 0.0], SparseVector(), alpha=0.0, top_k=5)
    assert "sparse_vector" not in pc.index.queries[-1]                                   # empty sparse vector never sent
    assert st.count() == 3


def test_pinecone_query_before_ingest_on_missing_index_is_a_clear_error():
    st = PineconeStore(None, "nope", client=FakePinecone(existing=()))
    with pytest.raises(RuntimeError, match="does not exist"):
        st.query([1.0], SparseVector(), 0.5, 5)


def test_cited_numbers_and_extractive_generator():
    assert cited_numbers("A [2]. B [1][2] C [7] D [0]", limit=3) == [2, 1]
    hits = [Hit(chunk(1, "Doc 1\nFirst sentence. Second one! Third."), 0.9), Hit(chunk(2, "Doc 2\nOnly one."), 0.5)]
    text = ExtractiveGenerator(max_passages=3, sentences=2).generate("q", hits)
    assert text == "First sentence. Second one! [1] Only one. [2]"
    assert ExtractiveGenerator().generate("q", []) == NOT_FOUND
    assert ExtractiveGenerator(min_score=0.95).generate("q", hits) == NOT_FOUND                      # top hit below the floor: decline
    assert ExtractiveGenerator(min_score=0.6).generate("q", hits) == "First sentence. Second one! [1]"   # second hit below the floor: dropped


class FakeChat:
    def __init__(self, reply):
        self.reply, self.calls = reply, []
        self.chat = self
        self.completions = self

    def create(self, **kw):
        self.calls.append(kw)
        return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": self.reply})()})()]})()


def test_openai_generator_prompt_has_numbered_passages_and_the_not_found_rule():
    fake = FakeChat("Losses are sampled lognormal [1].")
    gen = OpenAIGenerator("k", "gpt-4o-mini", client=fake)
    hits = [Hit(chunk(1, "Doc 1\nlognormal by default"), 0.9), Hit(Chunk(id="p#0", doc_id="p", title="Policy", collection="policies", url="u", heading_path=["Scope"], text="Policy — Scope\nfictional body", position=0, fictional=True), 0.4)]
    assert gen.generate("how are losses sampled?", hits) == "Losses are sampled lognormal [1]."
    kw = fake.calls[0]
    assert kw["model"] == "gpt-4o-mini" and kw["temperature"] == 0
    user = kw["messages"][1]["content"]
    assert "[1] Doc 1 — collection: faqs\nlognormal by default" in user and "[2] Policy › Scope — collection: policies (FICTIONAL demo content)" in user
    assert "I could not find this in the indexed documents" in kw["messages"][0]["content"]
    assert gen.generate("q", []) == NOT_FOUND


def _corpus(tmp_path: Path) -> Path:
    c = tmp_path / "corpus"
    (c / "faqs").mkdir(parents=True); (c / "policies").mkdir(); (c / "product-docs").mkdir()
    (c / "faqs" / "download-report.md").write_text("---\nid: faq-download\ntitle: How do I download a loss metrics report?\nfictional: true\n---\nOpen the analysis, choose Reports, then Loss Metrics, then Download. The file is a CSV with Gross, Net and Ceded columns.")
    (c / "policies" / "expenses.md").write_text("---\nid: pol-expenses\ntitle: Expenses policy\nfictional: true\n---\n# Conferences\nConference tickets up to 1500 USD are reimbursed with manager approval. Submit receipts within 30 days.")
    (c / "product-docs" / "footprint.md").write_text("---\nid: doc-footprint\ntitle: Footprint module\nurl: https://docs.example/footprint\n---\n# Importance level\nIf the company is not in the DFP the engine looks up Cat_SpofImportanceLevelFallback by scenario, SPoF, industry and size; the default importance level is 2.")
    return c


def test_pipeline_ingest_and_ask_round_trip_in_local_mode(tmp_path: Path, monkeypatch):
    s = Settings(_env_file=None, rag_mode="local", corpus_dir=_corpus(tmp_path), index_dir=tmp_path / "index")
    p = Pipeline(s)
    info = p.ingest()
    assert info["documents"] == 3 and info["chunks"] == 3 and info["store"] == "local" and info["embedder"] == "hash" and info["by_collection"]["faqs"] == 1
    a = p.ask("What is Cat_SpofImportanceLevelFallback?", alpha=0.0)
    assert a.found and a.citations[0].doc_id == "doc-footprint" and a.citations[0].url == "https://docs.example/footprint" and "[1]" in a.text and a.mode == "local"
    assert a.citations[0].heading == "Importance level" and 1 <= len(a.sources) <= 3 and a.generator == "extractive"
    b = p.ask("conference ticket reimbursement", alpha=0.5, collection="policies", top_k=2)
    assert b.citations[0].doc_id == "pol-expenses" and b.citations[0].fictional and all(src.collection == "policies" for src in b.sources)
    # a fresh pipeline reloads the saved index and encoder
    p2 = Pipeline(Settings(_env_file=None, rag_mode="local", corpus_dir=s.corpus_dir, index_dir=s.index_dir))
    assert p2.store.count() == 3 and p2.ask("download loss metrics report", alpha=0.0).citations[0].doc_id == "faq-download"
    none = p.ask("zzzz qqqq", alpha=0.0)
    assert none.text == NOT_FOUND and not none.found and not none.citations      # no known tokens: declines, never raises


def test_pipeline_ask_before_ingest_is_a_clear_error(tmp_path: Path):
    p = Pipeline(Settings(_env_file=None, rag_mode="local", corpus_dir=tmp_path, index_dir=tmp_path / "index"))
    with pytest.raises(RuntimeError, match="run `python -m rag ingest`"):
        p.ask("anything")


def test_evaluate_scores_recall_and_mrr_per_collection(tmp_path: Path):
    s = Settings(_env_file=None, rag_mode="local", corpus_dir=_corpus(tmp_path), index_dir=tmp_path / "index")
    p = Pipeline(s); p.ingest()
    queries = [EvalQuery("Cat_SpofImportanceLevelFallback default level", ["doc-footprint"], "product-docs"),
               EvalQuery("download loss metrics report", ["faq-download"], "faqs"),
               EvalQuery("conference reimbursement", ["doc-footprint"], "faqs", note="expected doc is in another collection: a miss, not an error"),
               EvalQuery("what colour is the sky", [], note="no answer in corpus: not scored")]
    res = evaluate(p.retriever, queries, alphas=(0.0, 0.5), k=5)
    assert [r.alpha for r in res] == [0.0, 0.5] and res[0].n == 3
    assert res[0].by_collection["product-docs"]["recall"] == 1.0 and res[0].by_collection["faqs"]["recall"] == 0.5 and "conference reimbursement" in res[0].misses
    assert 0 < res[0].mrr <= 1
    table = format_table(res)
    assert "sparse only" in table and "hybrid" in table and "product-docs: 1.00/1.00" in table


def test_cited_numbers_handles_lists_and_ranges():
    assert cited_numbers("A [1, 3]. B [2-4] C [02] D [9-7]", limit=4) == [1, 3, 2, 4]
    assert cited_numbers("nothing cited", limit=3) == []


def test_pinecone_existing_index_with_other_dimension_or_metric_is_refused_before_any_delete():
    class Described(FakePinecone):
        def __init__(self, dim, metric):
            super().__init__(existing=("enterprise-search",)); self.dim, self.metric = dim, metric
        def describe_index(self, name):
            return {"name": name, "dimension": self.dim, "metric": self.metric, "status": {"ready": True}}
    pc = Described(256, "dotproduct")
    with pytest.raises(RuntimeError, match="dimension 256"):
        PineconeStore(None, "enterprise-search", client=pc).reset(1536)
    assert pc.index.deleted == []
    pc = Described(1536, "cosine")
    with pytest.raises(RuntimeError, match="dotproduct"):
        PineconeStore(None, "enterprise-search", client=pc).reset(1536)
    assert pc.index.deleted == []
    PineconeStore(None, "enterprise-search", client=Described(1536, "dotproduct")).reset(1536)      # matching index: fine


def test_pinecone_reset_only_ignores_not_found():
    class Failing(FakeIndex):
        def delete(self, delete_all, namespace):
            raise RuntimeError("401 Unauthorized")
    pc = FakePinecone(existing=()); pc.index = Failing()
    with pytest.raises(RuntimeError, match="401"):
        PineconeStore(None, "enterprise-search", client=pc).reset(3)


def test_store_mode_needs_both_keys_in_auto():
    assert Settings(_env_file=None, pinecone_api_key="p").store_mode == "local"
    assert Settings(_env_file=None, pinecone_api_key="p", openai_api_key="o").store_mode == "pinecone"
    assert Settings(_env_file=None, pinecone_api_key="p", rag_mode="pinecone").store_mode == "pinecone"
    s = Settings(_env_file=None, pinecone_api_key="p-secret", openai_api_key="o-secret")
    assert "p-secret" not in repr(s) and "o-secret" not in str(s.describe()) and s.pinecone_key() == "p-secret"


def test_local_index_built_with_another_embedder_is_refused(tmp_path: Path):
    s = Settings(_env_file=None, rag_mode="local", corpus_dir=_corpus(tmp_path), index_dir=tmp_path / "index")
    Pipeline(s).ingest()
    other = Pipeline(s, embedder=HashEmbedder(dim=64))
    with pytest.raises(RuntimeError, match="built with embedder 'hash' \\(256-d\\)"):
        other.ask("anything")
    assert LocalStore.meta(s.index_dir)["embedder"] == "hash" and LocalStore.meta(s.index_dir)["dim"] == 256


def test_stem_and_coverage():
    from rag.sparse import stem, tokenize
    assert [stem(t) for t in ["vulnerabilities", "patched", "patching", "policies", "backups", "i38", "cat_x", "logs", "uses"]] == ["vulnerability", "patch", "patch", "policy", "backup", "i38", "cat_x", "logs", "uses"]
    enc = BM25Encoder().fit(["critical vulnerabilities are patched within days"])
    assert enc.coverage("how quickly must a critical vulnerability be patched") == 0.75        # only "quickly" is unknown; "must"/"how" are stop words
    assert enc.coverage("parental leave policy") == 0.0 and enc.coverage("") == 1.0
    assert tokenize("Patching cadence") == ["patch", "cadence"]


def test_evaluate_groups_by_expected_document_collection_and_counts_declines(tmp_path: Path):
    s = Settings(_env_file=None, rag_mode="local", corpus_dir=_corpus(tmp_path), index_dir=tmp_path / "index")
    p = Pipeline(s); p.ingest()
    queries = [EvalQuery("Cat_SpofImportanceLevelFallback default level", ["doc-footprint"]),
               EvalQuery("conference reimbursement", ["pol-expenses"], "faqs", note="filtered to the wrong collection: a miss grouped under policies"),
               EvalQuery("what colour is the sky", []), EvalQuery("conference tickets", [])]
    res = evaluate(p.retriever, queries, alphas=(0.5,), k=5, collection_of={"doc-footprint": "product-docs", "pol-expenses": "policies"},
                   ask=lambda q, a, c: p.ask(q, alpha=a, collection=c).text)
    r = res[0]
    assert set(r.by_collection) == {"product-docs", "policies"} and r.by_collection["policies"]["recall"] == 0.0
    assert r.declines_total == 2 and r.declines == 1 and r.false_answers == ["conference tickets"]      # the second "unanswerable" is answerable here
    assert "declines" in format_table(res) and "1/2" in format_table(res)


@pytest.mark.parametrize("alpha", [0.0, 0.5, 1.0])
def test_real_corpus_declines_out_of_corpus_questions_and_answers_in_corpus_ones_at_every_alpha(tmp_path: Path, alpha):
    from tools.make_corpus import write_corpus
    write_corpus(tmp_path / "corpus")
    s = Settings(_env_file=None, rag_mode="local", corpus_dir=tmp_path / "corpus", index_dir=tmp_path / "index")
    p = Pipeline(s); p.ingest()
    for q, coll in [("What is the capital of France?", None), ("What is our parental leave policy?", "policies"), ("zzqx unknownword", None)]:
        a = p.ask(q, alpha=alpha, collection=coll)
        assert a.text == NOT_FOUND and not a.found and a.citations == [], (q, alpha, a.text[:80])
    if alpha == 1.0:
        return                                   # dense-only with the lexical hash embedder is the known-weak setting; the eval table reports it, the test does not pin it
    for q, docs in [("How do I download a loss metrics report?", {"faq-download-loss-metrics", "doc-reports"}), ("Which scenarios use the hybrid footprint HFP?", {"doc-footprint-module"}),
                    ("how much can I spend on a hotel in London", {"pol-expenses-travel"})]:
        a = p.ask(q, alpha=alpha)
        assert a.found and a.citations[0].doc_id in docs, (q, alpha, [c.doc_id for c in a.sources])
