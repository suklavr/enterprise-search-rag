import math
from pathlib import Path

import pytest

from rag.chunking import chunk_document, sections, windows
from rag.dense import HashEmbedder
from rag.documents import Document, load_corpus, parse_front_matter
from rag.sparse import BM25Encoder, tokenize


def test_front_matter_parses_strings_lists_and_booleans(tmp_path: Path):
    raw = "---\nid: pol-1\ntitle: Expenses policy\ncollection: policies\ntags: [expenses, travel]\nfictional: true\n---\n# Expenses\nBody."
    meta, body = parse_front_matter(raw)
    assert meta == {"id": "pol-1", "title": "Expenses policy", "collection": "policies", "tags": ["expenses", "travel"], "fictional": True}
    assert body == "# Expenses\nBody."
    assert parse_front_matter("no front matter") == ({}, "no front matter")


def test_load_corpus_uses_folder_as_collection_and_rejects_duplicate_ids(tmp_path: Path):
    (tmp_path / "faqs").mkdir()
    (tmp_path / "faqs" / "a.md").write_text("---\nid: faq-a\ntitle: A\n---\nQ: a?\nA: yes.")
    (tmp_path / "faqs" / "b.md").write_text("# B heading\nplain body")
    docs = load_corpus(tmp_path)
    assert [(d.id, d.collection, d.title) for d in docs] == [("faq-a", "faqs", "A"), ("b", "faqs", "B heading")]
    assert docs[1].url == "internal://faqs/b"
    (tmp_path / "faqs" / "c.md").write_text("---\nid: faq-a\n---\ndup")
    with pytest.raises(ValueError, match="duplicate document id"):
        load_corpus(tmp_path)


def test_sections_and_windows():
    text = "intro line\n# One\nbody one\n## One A\nbody one a\n# Two\nbody two"
    assert sections(text) == [([], "intro line"), (["One"], "body one"), (["One", "One A"], "body one a"), (["Two"], "body two")]
    w = windows([str(i) for i in range(10)], max_words=4, overlap=1)
    assert w == [["0", "1", "2", "3"], ["3", "4", "5", "6"], ["6", "7", "8", "9"]]
    assert windows([], 4, 1) == [] and windows(["a"], 4, 1) == [["a"]]


def test_chunk_document_keeps_heading_path_and_handles_short_and_headingless_docs():
    long_body = "# Footprint\n" + " ".join(f"w{i}" for i in range(500)) + "\n## Detail\nshort tail"
    doc = Document(id="d", title="Doc", collection="product-docs", url="u", text=long_body)
    chunks = chunk_document(doc, max_words=200, overlap=50)
    assert [c.id for c in chunks] == ["d#0", "d#1", "d#2", "d#3"]
    assert chunks[0].heading_path == ["Footprint"] and chunks[3].heading_path == ["Footprint", "Detail"]
    assert chunks[0].text.startswith("Doc — Footprint\nw0 w1") and "w150" in chunks[1].text      # overlap carried over
    titled = chunk_document(Document(id="t", title="How do I reset?", collection="faqs", url="u", text="# How do I reset?\nUse the link."))
    assert titled[0].heading_path == [] and titled[0].text == "How do I reset?\nUse the link."       # heading equal to the title is not repeated
    plain = chunk_document(Document(id="p", title="Plain", collection="faqs", url="u", text="one short paragraph only"))
    assert len(plain) == 1 and plain[0].heading_path == [] and plain[0].text == "Plain\none short paragraph only"
    assert chunk_document(Document(id="e", title="Empty", collection="faqs", url="u", text="   ")) == []
    meta = chunks[3].to_metadata()
    from rag.chunking import Chunk
    assert Chunk.from_metadata("d#3", meta) == chunks[3]


def test_tokenize_keeps_identifiers_and_drops_stopwords():
    assert tokenize("The Cat_SpofImportanceLevelFallback table and I38 are used.") == ["cat_spofimportancelevelfallback", "table", "i38", "used"]


def test_bm25_idf_normalisation_and_unknown_tokens():
    enc = BM25Encoder().fit(["alpha beta gamma", "alpha beta", "alpha delta delta"])
    assert enc.vocab == {"alpha": 0, "beta": 1, "delta": 2, "gamma": 3}
    assert enc.idf[enc.vocab["alpha"]] < enc.idf[enc.vocab["beta"]] < enc.idf[enc.vocab["gamma"]]     # rarer = higher
    d = enc.encode_document("alpha delta delta")
    assert math.isclose(sum(v * v for v in d.values), 1.0, abs_tol=1e-9)
    assert d.as_dict()[enc.vocab["delta"]] > d.as_dict()[enc.vocab["alpha"]]                          # tf and idf both favour delta
    q = enc.encode_query("gamma unknownword")
    assert q.indices == [enc.vocab["gamma"]] and math.isclose(q.values[0], 1.0)
    assert not enc.encode_query("unknownword only") and not enc.encode_document("")


def test_bm25_round_trips_through_json(tmp_path: Path):
    enc = BM25Encoder().fit(["alpha beta", "beta gamma"])
    enc.save(tmp_path / "bm25.json")
    back = BM25Encoder.load(tmp_path / "bm25.json")
    assert back.vocab == enc.vocab and back.idf == enc.idf and back.encode_query("gamma").indices == enc.encode_query("gamma").indices


def test_hash_embedder_is_deterministic_unit_length_and_lexical():
    e = HashEmbedder(dim=64)
    a, b, c = e.embed(["footprint module market share", "footprint module market share", "expense reimbursement policy"])
    assert a == b and math.isclose(sum(v * v for v in a), 1.0, abs_tol=1e-9) and len(a) == 64
    dot_same = sum(x * y for x, y in zip(a, e.embed(["market share in the footprint module"])[0]))
    dot_other = sum(x * y for x, y in zip(a, c))
    assert dot_same > dot_other
    assert e.embed([""]) == [[0.0] * 64]
