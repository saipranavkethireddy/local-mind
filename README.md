# LocalMind 🛡️🧠

> **An air-gapped, privacy-first document intelligence workbench powered by local LLMs.**
>
> Built for the **Lenovo AI Challenge**.

---

## 💡 The Motivation

Modern productivity tools and document assistants often require users to upload confidential documents, such as resumes, financial records, academic transcripts, and proprietary reports, to third-party cloud servers.

This introduces significant risks:

- Privacy breaches and unauthorized data exposure.
- Data compliance and security vulnerabilities.
- Dependency on external cloud services.
- Vendor lock-in and recurring API costs.

**LocalMind** was engineered to solve this problem.

It provides a fast, privacy-first document querying environment that runs entirely on local hardware, ensuring that sensitive information remains under the user's control.

---

## 🏗️ System Architecture & Data Flow

LocalMind decouples document ingestion, local security filtering, context management, and offline inference to ensure complete data sovereignty.

```text
       [ PDF / DOC Upload ]
                |
                v
       [ Regex PII Scrubber ]
                |
                | Sanitizes emails, phone numbers
                | and sensitive identifiers
                v
       [ In-Memory Store ]
                |
                | Chunked context management
                v
       [ Local Ollama Runtime ]
                |
                | Executes Llama 3 locally
                | (Offline / Air-Gapped)
                v
       [ Glassmorphism UI ]
                |
                v
       [ Private, Locally Generated Responses ]
```

---

## 🔑 Key Features

### 1. 100% Air-Gapped & Offline

- Supports document querying without an active internet connection during inference.
- No external AI API calls.
- No cloud-based document processing or telemetry.
- Runs entirely on local hardware through Ollama.

### 2. Automated PII Redaction Pipeline

- Automatically identifies sensitive information in uploaded documents.
- Uses regex-based detection to scrub:
  - Email addresses.
  - Phone numbers.
  - Sensitive identifiers.
- Prevents detected personal information from entering the LLM context.

### 3. Optimized Local LLM Inference

- Powered by Meta's `llama3` model.
- Uses Ollama as the local inference runtime.
- Avoids external inference APIs.
- Designed for consumer hardware, including Apple Silicon devices.

### 4. High-End Developer UI

- Custom dark-mode interface.
- Glassmorphism-inspired visual design.
- Built using Tailwind CSS.
- Designed for an intuitive document querying experience.

---

## ⚡ Hardware & Performance Metrics

Optimized for modern consumer AI hardware, including Apple Silicon unified memory architectures.

| Component          | Configuration             |
| ------------------ | ------------------------- |
| Inference Engine   | Ollama                    |
| LLM                | `llama3:latest`           |
| Model Type         | Quantized                 |
| Memory Footprint   | ~4.7 GB RAM allocation    |
| Network Dependency | `localhost` (`127.0.0.1`) |
| Execution          | Local inference           |

---

## 🛠️ Tech Stack

| Layer                   | Technologies             |
| ----------------------- | ------------------------ |
| Backend                 | Python, FastAPI, Uvicorn |
| File Handling           | Python-Multipart         |
| Frontend                | HTML5, JavaScript (ES6+) |
| Styling                 | Tailwind CSS             |
| AI Runtime              | Ollama                   |
| LLM                     | Meta Llama 3             |
| Development Environment | macOS, Linux, VS Code    |

---

## 🔒 Privacy by Design

LocalMind follows a local-first architecture:

- Documents are processed locally.
- Sensitive identifiers are filtered before context injection.
- LLM inference happens through the local Ollama runtime.
- No external AI APIs are required during inference.
- Document context is maintained in memory rather than relying on cloud storage.

**Your documents. Your hardware. Your data.**

---

## 🎯 Project Objective

LocalMind demonstrates how modern AI-powered document intelligence can be implemented without compromising user privacy.

By combining local LLM inference, automated PII redaction, and a lightweight web interface, it aims to make private AI document processing accessible on consumer hardware.

**Built for the Lenovo AI Challenge.**
