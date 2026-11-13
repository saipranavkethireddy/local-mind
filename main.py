from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import shutil

from services.parser import DocumentParser
from services.llm import LocalLLMEngine
from services.redaction import PIIRedactor

app = FastAPI(title="LocalMind AI Workbench", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

DOCUMENT_STORE = {}

class QueryRequest(BaseModel):
    query: str
    model: str = "llama3"

class RedactRequest(BaseModel):
    text: str

@app.post("/api/ingest")
async def ingest_document(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        parsed_text = DocumentParser.parse_file(file_path)
        # Apply PII Redaction automatically on ingestion for privacy
        redacted_text, count = PIIRedactor.redact_text(parsed_text)
        DOCUMENT_STORE[file.filename] = redacted_text
        return {"status": "success", "filename": file.filename, "pii_redactions_made": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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