# LocalMind 🛡️🧠

> **An air-gapped, privacy-first document intelligence workbench powered by local LLMs.** Built for the Lenovo AI Challenge.

---

## 💡 The Motivation

Modern productivity tools and document assistants force users to upload confidential resumes, financial records, academic transcripts, and proprietary reports to opaque third-party cloud servers. This introduces severe privacy risks, data compliance vulnerabilities, and vendor lock-in.

**LocalMind** was engineered to solve this. It provides a lightning-fast, zero-telemetry document querying environment that runs entirely on local hardware—ensuring your sensitive data never leaves your machine.

---

## 🏗️ System Architecture & Data Flow

LocalMind decouples ingestion, local security filtering, and offline inference to guarantee complete data sovereignty:

```text
  [ PDF / Doc Upload ]
          │
          ▼
  [ Regex PII Scrubber ]  ──> Sanitizes emails, phone numbers & identifiers
          │
          ▼
  [ In-Memory Store  ]  ──> Chunked context management
          │
          ▼
  [ Local Ollama Runtime ] ──> Executes Llama 3 (Offline / Air-Gapped)
          │
          ▼
  [ Glassmorphism UI ]  ──> Instant, private responses delivered locally

---

🔑 **Key Features**
* **100% Air-Gapped & Offline:** Operates without an active internet connection during inference; zero external API calls or telemetry.
* **Automated PII Redaction Pipeline:** Intercepts uploaded documents to scrub sensitive personal identifiers before context injection.
* **Optimized Local LLM Inference:** Powered by Meta's `llama3` running locally via Ollama.
* **High-End Developer UI:** Custom dark-mode glassmorphism interface built with Tailwind CSS, designed for heavy developer workflows.

---

⚡ **Hardware & Performance Metrics**

Optimized for modern consumer AI hardware (including Apple Silicon unified memory architectures):
* **Inference Engine:** Ollama (`llama3:latest`, quantized)
* **Memory Footprint:** ~4.7 GB RAM/VRAM allocation
* **Network Dependency:** Strictly `localhost` (`127.0.0.1`)

---

🛠️ **Tech Stack**
* **Backend:** Python, FastAPI, Uvicorn, Python-Multipart
* **Frontend:** HTML5, Tailwind CSS (Custom Glassmorphism theme), JavaScript (ES6+)
* **AI Runtime:** Ollama (`llama3`)
* **Environment:** macOS / Linux, VS Code
```
