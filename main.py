import json

from urllib.parse import quote
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import os
import tempfile
import uuid
from pathlib import Path
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from services.parser import DocumentParser
from services.llm import LocalLLMEngine
from services.redaction import PIIRedactor
from services.hybrid import HybridRetriever
from services.retriever import build_context


RETRIEVER = HybridRetriever()
TOP_K = 5

async def _retrieve(query: str):
    """Performs hybrid search and builds context with source tracing."""
    chunks = await RETRIEVER.search_hybrid(query, k=TOP_K)
    sources = [{"file": c.doc, "part": c.index + 1, "snippet": c.text[:200]} for c in chunks]
    return build_context(chunks), sources

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}  # <- set to what DocumentParser supports
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

app = FastAPI(title="LocalMind AI Workbench", version="1.0.0")

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

ALLOWED_MODELS = {m.strip() for m in os.getenv("LOCALMIND_MODELS", "llama3").split(",")}

DOCUMENT_STORE = {}

class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    model: str = "llama3"

class RedactRequest(BaseModel):
    text: str = Field(max_length=200_000)

def _check_model(model: str) -> None:
    if model not in ALLOWED_MODELS:
        raise HTTPException(400, f"Model not allowed. Choose one of: {sorted(ALLOWED_MODELS)}")

@app.post("/api/ingest")
async def ingest_document(file: UploadFile = File(...)):
    display_name = Path(file.filename or "upload").name   # strips any ../ parts
    suffix = Path(display_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type {suffix or '(none)'}.")

    # The raw (unredacted) file only exists inside a temp dir that is wiped on exit.
    with tempfile.TemporaryDirectory(prefix="localmind_") as tmp:
        tmp_path = Path(tmp) / f"{uuid.uuid4().hex}{suffix}"
        size = 0
        with open(tmp_path, "wb") as buf:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "File too large (limit 20 MB).")
                buf.write(chunk)
        try:
            parsed_text = await run_in_threadpool(DocumentParser.parse_file, str(tmp_path))
        except Exception:
            raise HTTPException(400, "Could not read this file. Is it a valid, non-encrypted document?")

    redacted_text, count = PIIRedactor.redact_text(parsed_text)
    n_chunks, embedded = await RETRIEVER.add_document_async(display_name, redacted_text)
    return {
        "status": "success",
        "filename": display_name,
        "pii_redactions_made": count,
        "chunks": n_chunks,
        "semantic_search": embedded,
    }

@app.post("/api/query")
async def query_documents(req: QueryRequest):
    _check_model(req.model)

    if not RETRIEVER.chunks:
        return {
            "response": "No documents currently ingested in the local workspace. Please upload files first.", 
            "sources_used": []
        }
    
    # Retrieve top-k hybrid chunks and build context dynamically
    context, sources = await _retrieve(req.query)
    
    answer = await LocalLLMEngine.generate_response(req.query, context, req.model)
    
    # Extract unique filenames used in the sources
    unique_files = list({s["file"] for s in sources})
    
    return {
        "response": answer["text"], 
        "sources_used": unique_files,
        "sources_detailed": sources,
        "stats": answer.get("stats")
    }

@app.post("/api/query/stream")
async def query_documents_stream(req: QueryRequest):
    _check_model(req.model)
    if not RETRIEVER:
        raise HTTPException(400, "No documents ingested yet. Please upload a file first.")
    context, sources = await _retrieve(req.query)
    headers = {"X-Sources": quote(json.dumps(sources)), "Cache-Control": "no-store"}
    return StreamingResponse(
        LocalLLMEngine.stream_response(req.query, context, req.model),
        media_type="text/plain; charset=utf-8",
        headers=headers,
    )

@app.get("/api/documents")
async def list_documents():
    # Extract unique document names from the retriever chunks
    doc_names = list({chunk.doc for chunk in RETRIEVER.chunks})
    return {"documents": doc_names}

@app.post("/api/redact")
async def redact_text_endpoint(req: RedactRequest):
    cleaned_text, count = PIIRedactor.redact_text(req.text)
    return {"redacted_text": cleaned_text, "redactions_count": count}


# Mount static frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)