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

    def add_document(self, name: str, text: str, chunk_size: int = 300, overlap: int = 50) -> int:
        """Synchronously chunks a document and updates BM25 statistics. Returns number of chunks."""
        self.chunks = [c for c in self.chunks if c.doc != name]
        words = text.split()
        new_chunks = []
        start_idx = len(self.chunks)
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_text = " ".join(words[i:i + chunk_size])
            if chunk_text.strip():
                chunk = Chunk(doc=name, index=start_idx + len(new_chunks), text=chunk_text)
                new_chunks.append(chunk)

        self.chunks.extend(new_chunks)
        self._recompute_bm25_stats()
        return len(new_chunks)

    def remove_document(self, name: str) -> None:
        """Removes a document's chunks and recomputes BM25 statistics."""
        self.chunks = [c for c in self.chunks if c.doc != name]
        self._recompute_bm25_stats()

    def _recompute_bm25_stats(self):
        self.N = len(self.chunks)
        if self.N == 0:
            self.doc_freqs.clear()
            self.idf.clear()
            self.avgdl = 0
            return

        self.doc_freqs.clear()
        doc_lens = []
        for chunk in self.chunks:
            tokens = tokenize(chunk.text)
            doc_lens.append(len(tokens))
            for t in set(tokens):
                self.doc_freqs[t] += 1

        self.avgdl = sum(doc_lens) / self.N if self.N > 0 else 0
        for term, freq in self.doc_freqs.items():
            self.idf[term] = math.log(1 + (self.N - freq + 0.5) / (freq + 0.5))

    def search(self, query: str, k: int = 5, fallback: bool = True) -> list[Chunk]:
        """Performs lexical BM25 search over chunks."""
        query_tokens = tokenize(query)
        scores = {}
        
        for idx, chunk in enumerate(self.chunks):
            tokens = tokenize(chunk.text)
            dl = len(tokens)
            tf = Counter(tokens)
            score = 0.0
            
            for qt in query_tokens:
                if qt not in self.idf:
                    continue
                f = tf[qt]
                num = f * (self.k1 + 1)
                den = f + self.k1 * (1 - self.b + self.b * (dl / self.avgdl if self.avgdl > 0 else 1))
                score += self.idf[qt] * (num / den)
                
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