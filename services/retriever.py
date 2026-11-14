import math
import re
from collections import Counter
from dataclasses import dataclass

_WORD = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", 
    "were", "be", "it", "this", "that", "with", "as", "at", "by", "from", "what", 
    "which", "who", "how", "do", "does", "did", "i", "me", "my", "you", "your"
}

def tokenize(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if w not in _STOP]

@dataclass
class Chunk:
    doc: str
    index: int
    text: str

class Retriever:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: list[Chunk] = []
        self.doc_freqs = Counter()
        self.idf = {}
        self.avgdl = 0
        self.N = 0
        # Per-chunk term counts and lengths, aligned with self.chunks.
        # Built once when documents change, so a query never re-tokenizes text.
        self._tf: list[Counter] = []
        self._dl: list[int] = []
        # Original (redacted) text of each document, kept so small workspaces can be
        # sent to the model whole instead of as overlapping chunks.
        self.docs: dict[str, str] = {}

    def add_document(self, name: str, text: str, chunk_size: int = 300, overlap: int = 50) -> int:
        """Synchronously chunks a document and updates BM25 statistics. Returns number of chunks."""
        self.chunks = [c for c in self.chunks if c.doc != name]
        self.docs[name] = text
        words = text.split()
        new_chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_text = " ".join(words[i:i + chunk_size])
            if chunk_text.strip():
                # index is the position inside this document (0, 1, 2, ...)
                chunk = Chunk(doc=name, index=len(new_chunks), text=chunk_text)
                new_chunks.append(chunk)

        self.chunks.extend(new_chunks)
        self._recompute_bm25_stats()
        return len(new_chunks)

    def remove_document(self, name: str) -> None:
        """Removes a document's chunks and recomputes BM25 statistics."""
        self.chunks = [c for c in self.chunks if c.doc != name]
        self.docs.pop(name, None)
        self._recompute_bm25_stats()

    def total_words(self) -> int:
        return sum(len(t.split()) for t in self.docs.values())

    def full_context(self) -> tuple[str, list[dict]]:
        """Whole documents in upload order, plus matching source entries."""
        parts, sources = [], []
        for name, text in self.docs.items():
            parts.append(f"=== File: {name} (complete) ===\n{text}")
            sources.append({"file": name, "part": "whole document", "snippet": text[:200]})
        return "\n\n".join(parts), sources

    def _recompute_bm25_stats(self):
        self.N = len(self.chunks)
        self.doc_freqs.clear()
        self.idf.clear()
        self._tf = []
        self._dl = []
        if self.N == 0:
            self.avgdl = 0
            return

        for chunk in self.chunks:
            tokens = tokenize(chunk.text)
            self._tf.append(Counter(tokens))
            self._dl.append(len(tokens))
            for t in set(tokens):
                self.doc_freqs[t] += 1

        self.avgdl = sum(self._dl) / self.N
        for term, freq in self.doc_freqs.items():
            self.idf[term] = math.log(1 + (self.N - freq + 0.5) / (freq + 0.5))

    def search(self, query: str, k: int = 5, fallback: bool = True) -> list[Chunk]:
        """Performs lexical BM25 search over chunks."""
        # Safety net: if chunks were changed without going through add/remove.
        if len(self._tf) != len(self.chunks):
            self._recompute_bm25_stats()

        query_tokens = [t for t in tokenize(query) if t in self.idf]
        scores = {}

        if query_tokens:
            for idx in range(len(self.chunks)):
                tf = self._tf[idx]
                dl = self._dl[idx]
                norm = 1 - self.b + self.b * (dl / self.avgdl if self.avgdl > 0 else 1)
                score = 0.0

                for qt in query_tokens:
                    f = tf.get(qt, 0)
                    if f:
                        score += self.idf[qt] * (f * (self.k1 + 1)) / (f + self.k1 * norm)

                if score > 0:
                    scores[idx] = score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = [self.chunks[idx] for idx, score in ranked[:k]]
        
        if not results and fallback and self.chunks:
            return self.chunks[:k]
            
        return results

def build_context(chunks: list[Chunk]) -> str:
    """Formats retrieved chunks into a clean context string for the LLM."""
    if not chunks:
        return "No relevant context found."
    
    formatted_parts = []
    for chunk in chunks:
        formatted_parts.append(f"=== File: {chunk.doc} (Part {chunk.index + 1}) ===\n{chunk.text}")
    
    return "\n\n".join(formatted_parts)