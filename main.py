from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import tempfile
import uuid
from pathlib import Path
from fastapi.concurrency import run_in_threadpool

from services.parser import DocumentParser
from services.llm import LocalLLMEngine
from services.redaction import PIIRedactor

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}  # <- set to what DocumentParser supports
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

app = FastAPI(title="LocalMind AI Workbench", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCUMENT_STORE = {}

class QueryRequest(BaseModel):
    query: str
    model: str = "llama3"

class RedactRequest(BaseModel):
    text: str

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
    DOCUMENT_STORE[display_name] = redacted_text
    return {"status": "success", "filename": display_name, "pii_redactions_made": count}

@app.post("/api/query")
async def query_documents(req: QueryRequest):
    if not DOCUMENT_STORE:
        return {"response": "No documents currently ingested in the local workspace. Please upload files first.", "sources_used": []}
    
    combined_context = "\n\n".join([f"=== File: {fname} ===\n{content}" for fname, content in DOCUMENT_STORE.items()])
    answer = await LocalLLMEngine.generate_response(req.query, combined_context, req.model)
    return {"response": answer, "sources_used": list(DOCUMENT_STORE.keys())}

@app.post("/api/redact")
async def redact_text_endpoint(req: RedactRequest):
    cleaned_text, count = PIIRedactor.redact_text(req.text)
    return {"redacted_text": cleaned_text, "redactions_count": count}

@app.get("/api/documents")
async def list_documents():
    return {"documents": list(DOCUMENT_STORE.keys())}

# Mount static frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)