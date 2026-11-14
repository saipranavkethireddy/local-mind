"""Hybrid search: BM25 (exact words) + local embeddings (meaning), merged with
Reciprocal Rank Fusion. Embeddings come from Ollama, so everything stays on-device."""
import os

import httpx
import numpy as np

from services.retriever import Chunk, Retriever

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = os.getenv("LOCALMIND_EMBED_MODEL", "nomic-embed-text")
RRF_K = 60       # standard constant from the original RRF paper
POOL = 20        # candidates taken from each search before fusion
BATCH = 32


async def ollama_embed(texts: list[str], prefix: str) -> np.ndarray | None:
    """Return L2-normalised vectors, or None if embeddings are unavailable
    (Ollama down, model not pulled). The caller then falls back to BM25 only."""
    try:
        out: list[list[float]] = []
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=120, write=30, pool=5)) as c:
            for i in range(0, len(texts), BATCH):
                batch = [prefix + t for t in texts[i:i + BATCH]]
                r = await c.post(
                    f"{OLLAMA_URL}/api/embed",
                    # keep_alive: don't unload the embedding model after 5 idle minutes,
                    # otherwise the next question pays a model reload.
                    json={"model": EMBED_MODEL, "input": batch, "keep_alive": "30m"},
                )
                r.raise_for_status()
                out.extend(r.json()["embeddings"])
        m = np.asarray(out, dtype=np.float32)
        norms = np.linalg.norm(m, axis=1, keepdims=True)
        return m / np.clip(norms, 1e-9, None)
    except (httpx.HTTPError, KeyError, ValueError):
        return None


def rrf(rankings: list[list[tuple]], k: int = RRF_K) -> list[tuple]:
    """Reciprocal Rank Fusion. Each ranking is a list of keys, best first.
    A key's score is the sum of 1/(k+rank) over every list it appears in."""
    scores: dict[tuple, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking, start=1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)


class HybridRetriever(Retriever):
    def __init__(self, embedder=ollama_embed):
        super().__init__()
        self.embedder = embedder
        self.vecs: dict[tuple[str, int], np.ndarray] = {}
        self._dense = None  # cached (keys, matrix); rebuilt lazily after any change

    def _drop_vectors(self, name: str) -> None:
        self.vecs = {k: v for k, v in self.vecs.items() if k[0] != name}
        self._dense = None

    def remove_document(self, name: str) -> None:
        super().remove_document(name)
        self._drop_vectors(name)

    async def add_document_async(self, name: str, text: str) -> tuple[int, bool]:
        """Returns (number_of_chunks, embeddings_available)."""
        # Re-uploading a file must not leave the old version's vectors behind:
        # they would crowd the dense results or, if embedding fails now,
        # point at the wrong text.
        self._drop_vectors(name)
        n = self.add_document(name, text)
        chunks = [c for c in self.chunks if c.doc == name]
        vecs = await self.embedder([c.text for c in chunks], "search_document: ")
        if vecs is not None:
            for c, v in zip(chunks, vecs):
                self.vecs[(c.doc, c.index)] = v
            self._dense = None
        return n, vecs is not None

    def _dense_index(self):
        if self._dense is None:
            keys = list(self.vecs.keys())
            self._dense = (keys, np.stack([self.vecs[k] for k in keys]))
        return self._dense

    async def search_hybrid(self, query: str, k: int = 5) -> list[Chunk]:
        if not self.chunks:
            return []
        by_key = {(c.doc, c.index): c for c in self.chunks}

        lexical = [(c.doc, c.index) for c in self.search(query, k=POOL, fallback=False)]

        dense: list[tuple] = []
        if self.vecs:
            qv = await self.embedder([query], "search_query: ")
            if qv is not None:
                keys, matrix = self._dense_index()
                sims = matrix @ qv[0]
                order = np.argsort(-sims)[:POOL]
                dense = [keys[i] for i in order]

        if not lexical and not dense:
            return self.search(query, k=k, fallback=True)   # e.g. "summarize this"
        fused = rrf([r for r in (lexical, dense) if r])
        return [by_key[key] for key in fused[:k] if key in by_key]