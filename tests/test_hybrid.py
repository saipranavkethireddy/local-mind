import asyncio
import numpy as np
from services.hybrid import HybridRetriever, rrf

CONCEPTS = [
    {"university", "college", "education", "iit", "delhi", "degree", "b.tech"},
    {"grocery", "milk", "eggs", "bread", "shopping"},
    {"skills", "python", "c++", "fastapi", "programming"},
]

async def fake_embed(texts, prefix):
    vecs = []
    for t in texts:
        words = set(t.lower().replace(",", " ").replace(".", " ").replace(":", " ").split())
        v = np.array([len(words & grp) for grp in CONCEPTS], dtype=np.float32) + 1e-3
        vecs.append(v / np.linalg.norm(v))
    return np.stack(vecs)

async def none_embed(texts, prefix):
    return None

def run(coro):
    return asyncio.run(coro)

def make(embedder):
    r = HybridRetriever(embedder=embedder)
    run(r.add_document_async("cv.txt", "Skills: Python, C++, FastAPI.\n\n" + "filler " * 200 + "\n\nEducation: B.Tech at IIT Delhi."))
    run(r.add_document_async("notes.txt", "Grocery list: milk, eggs, bread."))
    return r

def test_rrf_rewards_agreement():
    assert rrf([["a", "b", "c"], ["d", "b", "e"]])[0] == "b"

def test_rrf_single_list_keeps_order():
    assert rrf([["x", "y", "z"]]) == ["x", "y", "z"]

def test_semantic_match_bm25_alone_misses():
    r = make(fake_embed)
    # BM25 alone: no word overlap with "university" -> nothing lexical
    assert r.search("which university", k=2, fallback=False) == []
    top = run(r.search_hybrid("which university did he attend", k=2))
    assert any("IIT Delhi" in c.text for c in top)

def test_exact_keyword_still_found():
    r = make(fake_embed)
    top = run(r.search_hybrid("FastAPI", k=1))
    assert "FastAPI" in top[0].text

def test_falls_back_to_bm25_when_embeddings_unavailable():
    r = make(none_embed)
    assert not r.vecs
    top = run(r.search_hybrid("grocery list", k=1))
    assert top[0].doc == "notes.txt"

def test_reupload_replaces_vectors():
    r = make(fake_embed)
    before = len([k for k in r.vecs if k[0] == "notes.txt"])
    run(r.add_document_async("notes.txt", "Milk."))
    after = [k for k in r.vecs if k[0] == "notes.txt"]
    assert before >= 1 and len(after) == 1

def test_summarize_style_query_still_returns_something():
    r = make(none_embed)
    assert run(r.search_hybrid("summarize", k=3))