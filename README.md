# LocalMind 🛡️🧠

> **A privacy-first document Q&A workbench that runs entirely on your own machine.**
> Your files are parsed, redacted, indexed and answered locally with Ollama. After the
> one-time model download, nothing leaves the computer.
>
> Built for the **Lenovo AI Challenge**.

---

## 🚀 Quick start

Requires Python 3.10+ and [Ollama](https://ollama.com).

```bash
# 1. Pull the two models once (needs internet)
ollama pull llama3
ollama pull nomic-embed-text

# 2. Install and run
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
# open http://localhost:8000
```

Optional: `pip install pypdfium2` gives better text extraction on some PDFs
(the parser uses it automatically when installed, and falls back to `pypdf` otherwise).

**Check the offline claim yourself:** after the models are pulled, turn Wi-Fi off,
upload a file and ask a question. The app only talks to Ollama on `127.0.0.1`, and the
interface is a single HTML file with no CDN, fonts or framework downloads.

---

## ✨ What it does

- **Upload** PDF, DOCX, XLSX, TXT or Markdown files (up to 20 MB each).
- **Redacts** sensitive identifiers _before_ anything is indexed or sent to the model.
- **Finds the right passages** with hybrid search (keyword + meaning).
- **Streams answers** word by word from a local Llama 3 model.
- **Shows its sources** for every answer: file name, part number and a snippet.
- **Refuses to guess**: if the answer is not in the documents, the model is instructed to say so.

---

## 🏗️ How it works

```text
  PDF / DOCX / XLSX / TXT / MD upload
                |
                v
        [ Parser ]  text extraction, tables kept, no OCR
                |
                v
        [ PII redaction ]  regex, runs before indexing
                |
                v
        [ Index, in memory ]
          - ~300-word chunks, 50-word overlap
          - BM25 keyword index
          - nomic-embed-text vectors (via Ollama)
                |
                v
   small workspace (<= 1,800 words)?
        yes -> send the complete documents
        no  -> hybrid search: BM25 + vectors, merged with
               Reciprocal Rank Fusion, top 4 chunks
                |
                v
        [ Ollama + Llama 3 ]  streamed response
                |
                v
        [ Browser UI ]  answer + source passages
```

### Design decisions

- **Hybrid retrieval.** BM25 is strong on exact terms (names, IDs, error codes) and weak on
  paraphrase. Embeddings are the opposite. Reciprocal Rank Fusion (k = 60, 20 candidates from
  each) merges the two ranked lists without having to normalise their very different scores.
- **Whole-document mode for small workspaces.** Top-k retrieval cannot answer questions about
  the document as a whole ("how many questions are there?", "what is the first question?"),
  because the model only sees a few excerpts. When everything uploaded is small enough, the
  full text is sent instead. Each prompt starts with a note telling the model whether it sees the
  whole document or only excerpts, and it is told not to guess counts in the second case.
- **Redact first.** Redaction happens right after parsing, so identifiers never reach the
  index, the embedding model or the LLM.
- **Documents are untrusted input.** The system prompt tells the model to ignore any
  instructions that appear inside a document. This reduces prompt-injection risk but does not
  eliminate it.
- **Graceful degradation.** If the embedding model is unavailable, search falls back to BM25
  only, and the interface says so.

---

## 🛡️ What gets redacted (and what doesn't)

Replaced with `[REDACTED_...]` tags: email addresses, Indian mobile numbers, Luhn-valid card
numbers, Aadhaar-format IDs and PAN numbers.

**Not** detected: names, postal addresses, dates of birth, passport numbers. Regex cannot reliably
find these. Treat redaction as a safety net, not a guarantee. Text you type into the question box
is not redacted.

---

## ⚙️ Configuration

All optional, set as environment variables.

| Variable                  | Default                  | Purpose                                                 |
| ------------------------- | ------------------------ | ------------------------------------------------------- |
| `OLLAMA_URL`              | `http://127.0.0.1:11434` | Where Ollama is running                                 |
| `LOCALMIND_MODELS`        | `llama3`                 | Comma-separated list of chat models the API accepts     |
| `LOCALMIND_MODEL`         | `llama3`                 | Default chat model                                      |
| `LOCALMIND_EMBED_MODEL`   | `nomic-embed-text`       | Embedding model                                         |
| `LOCALMIND_NUM_CTX`       | `4096`                   | Context window passed to Ollama                         |
| `LOCALMIND_TOP_K`         | `4`                      | Chunks sent to the model in retrieval mode              |
| `LOCALMIND_FULLDOC_WORDS` | `1800`                   | Largest workspace sent whole; `0` always uses retrieval |

To try a faster, smaller model: `ollama pull llama3.2:3b`, add it to `LOCALMIND_MODELS`, and
change `MODEL` at the top of the script in `static/index.html`.

---

## 🔌 API

| Endpoint                 | Purpose                                                                                           |
| ------------------------ | ------------------------------------------------------------------------------------------------- |
| `POST /api/ingest`       | Upload a file; returns chunk count, redaction count and whether semantic search is available      |
| `POST /api/query/stream` | Streams the answer as plain text; the sources arrive in the `X-Sources` response header           |
| `POST /api/query`        | Same question, full answer at once, with timing stats (tokens per second, load time, prompt time) |
| `GET /api/documents`     | Documents currently indexed                                                                       |
| `POST /api/redact`       | Run the redactor on text and see what it removes                                                  |

---

## 🔒 Privacy and security

- Everything is held in memory. Nothing is written to disk except a temporary copy of the upload
  while it is being parsed, which is deleted immediately. Restarting the server clears the index.
- The server listens on `127.0.0.1` only, accepts only `localhost` / `127.0.0.1` host headers,
  and restricts CORS to its own origin.
- Uploads are limited to 20 MB and to known file types. File names are stripped of any path
  components.
- Only models listed in `LOCALMIND_MODELS` can be requested.
- Messages are rendered as text, never as HTML, so document or model output cannot inject markup.
- There is no login. It is a single-user tool for your own machine, and every upload goes into one
  shared workspace.

---

### 📊 Measured Performance (Apple Silicon M4)

Tested locally on your hardware running Llama 3 via Ollama:

| Metric                  | Value                      | Description                              |
| :---------------------- | :------------------------- | :--------------------------------------- |
| **Machine**             | Apple Silicon ARM (Darwin) | Local hardware execution                 |
| **Model**               | Llama 3 (`llama3:latest`)  | Fully air-gapped local model             |
| **Time to First Token** | **0.08 s**                 | Ultra-low latency startup for generation |
| **Generation Speed**    | **19.8 tokens/s**          | High-throughput local token streaming    |

---

## ⚠️ Limitations

- **No OCR.** Scanned or image-only PDFs are rejected with a clear message.
- **Equations.** Text extraction on math-heavy PDFs (LaTeX) can scramble formulas, and a
  text-only model cannot read equations from images.
- **Large documents.** Above the whole-document limit, the model sees only the top few passages,
  so counting or listing everything is unreliable.
- **Redaction is regex-based** and misses names, addresses and similar free-form identifiers.
- **In-memory only.** No persistence and no per-user separation.
- **Answer quality** is that of an 8B-parameter local model: good for lookups and summaries of
  short material, weaker at multi-step reasoning.

## 🗺️ Roadmap

- Retrieval evaluation: recall@k for BM25 only, embeddings only and hybrid on a labelled question set.
- NER-based redaction (names, addresses) with measured precision and recall.
- Testing on Windows / Intel and AMD AI PC hardware, including NPU-accelerated runtimes.
- OCR for scanned documents, and optional on-disk encrypted persistence.

---

## 🧱 Project layout

```text
main.py               FastAPI app, routes, upload handling, retrieval mode selection
services/parser.py    PDF, DOCX, XLSX, TXT, MD text extraction
services/redaction.py Regex PII redaction (with Luhn check for cards)
services/retriever.py Chunking and BM25
services/hybrid.py    Embeddings, Reciprocal Rank Fusion, hybrid search
services/llm.py       Ollama client, system prompt, streaming
static/index.html     Single-file interface (plain HTML, CSS, JS)
```

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## 💡 Why this exists

Document assistants usually ask you to upload resumes, financial records, transcripts and internal
reports to someone else's servers. That brings privacy and compliance risks, a dependency on cloud
services, and recurring API costs. LocalMind shows that useful document Q&A can run on an ordinary
laptop, with your files staying under your control.

**Your documents. Your hardware. Your data.**
