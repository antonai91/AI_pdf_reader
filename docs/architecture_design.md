# Architecure Design — PDF Reader App with Chat & Table Extraction

This file defines the architecture, tech stack, conventions, and implementation rules
for this project. Follow these instructions precisely when generating or modifying code.

---

## Project Overview

A **local-first** performant web application that allows users to:

1. **Upload and view PDFs** in a split-panel UI
2. **Chat with the document** via an AI-powered chat panel on the right
3. **Extract tables** from PDFs and export them as `.xlsx` spreadsheets
4. **OCR scanned PDFs** using a local model

Everything runs on the user's machine. No cloud services, no external storage, no SaaS dependencies.

---

## High-Level Architecture

```
┌────────────────────────────────────────────┐
│         Next.js 14 Frontend (TypeScript)   │
│  - PDF viewer (left panel)                 │
│  - Chat interface (right panel)            │
│  - Table extraction + Excel download       │
└──────────────────┬─────────────────────────┘
                   │ HTTP / SSE
┌──────────────────▼─────────────────────────┐
│         FastAPI Backend (Python)           │
│  - OpenAI SDK (GPT-4o chat + tool use)     │
│  - LangChain + FAISS RAG pipeline          │
│  - mlx-lm Qwen embeddings (local)          │
│  - GLM-OCR-MLX (local OCR)                 │
│  - DiskCache (chunk + embedding cache)     │
│                                            │
│   import pdf_engine      ◄─────────────────┼─┐
│   import table_extractor ◄─────────────────┼─┤ Rust V2 (PyO3)
│   import excel_writer    ◄─────────────────┼─┘
└──────────────────┬─────────────────────────┘
                   │
┌──────────────────▼─────────────────────────┐
│         Local Storage                      │
│  - ./data/pdfs/        (uploaded PDFs)     │
│  - ./data/faiss/       (FAISS indexes)     │
│  - ./data/cache/       (DiskCache)         │
│  - ./data/ocr_output/  (OCR text files)    │
└────────────────────────────────────────────┘
```

---

## Tech Stack

### Frontend

- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript (strict mode, no `any`)
- **Styling**: TailwindCSS + shadcn/ui components
- **PDF Viewer**: `react-pdf` (PDF.js under the hood, Web Workers enabled)
- **Chat**: Vercel AI SDK (`useChat` hook, SSE streaming)
- **Data fetching**: TanStack Query v5 for caching and async state
- **Excel download**: SheetJS (`xlsx`) client-side, no server round-trip

### Backend

- **Framework**: FastAPI (Python 3.12+)
- **Package manager**: `uv` (never use pip directly)
- **AI SDK**: `openai` (official Python SDK, streaming enabled, GPT-4o)
- **Embeddings**: `mlx-lm` with **Qwen embedding model** — runs fully local via Apple MLX
- **RAG pipeline**: `langchain` + `langchain-community` with **FAISS** vector store
- **Vector store**: FAISS (local, persisted to `./data/faiss/`)
- **PDF parsing**: `PyMuPDF` (`fitz`) — primary parser for all PDF text and layout extraction
- **OCR**: `GLM-OCR-MLX` — local OCR model for scanned/image-based PDFs
- **Chunk cache**: `diskcache` — disk-based key/value cache, keyed by SHA-256 of PDF bytes
- **Rust bridge**: PyO3 modules compiled with `maturin` (V2, see below)

### Rust Modules — V2 (PyO3 via Maturin)

Use Rust **only** for computationally intensive tasks. Never rewrite logic in Rust
that is already fast enough in Python.

| Module | Crate(s) | Responsibility |
|---|---|---|
| `pdf_engine` | `lopdf`, `pdfium-render` | Parse large PDFs, extract raw bytes + coordinates at speed |
| `table_extractor` | custom | Cluster text by coordinates into table rows/columns (CPU-bound) |
| `excel_writer` | `rust_xlsxwriter` | Write large `.xlsx` files fast |

> **V2 note**: Rust modules are optional enhancements, not required for the app to run.
> Python must always fall back gracefully (see fallback rules below).

### Local Storage Layout

```
./data/
├── pdfs/           # Raw uploaded PDF files, named by SHA-256 hash
├── faiss/          # Persisted FAISS indexes, one per file_id
├── cache/          # DiskCache directory (chunks, metadata)
└── ocr_output/     # Extracted text from GLM-OCR-MLX, cached as .txt
```

All paths are relative to the backend root. Configurable via `.env`.

---

## Project Structure

```
/
├── frontend/                  # Next.js app
│   ├── app/
│   │   ├── page.tsx           # Main split-panel layout
│   │   ├── api/               # Next.js API routes (thin proxies only)
│   │   └── layout.tsx
│   ├── components/
│   │   ├── PDFViewer.tsx      # react-pdf viewer, Web Workers
│   │   ├── ChatPanel.tsx      # useChat streaming panel
│   │   ├── TableExtractor.tsx # Trigger extraction, show preview, download
│   │   └── ui/                # shadcn/ui primitives
│   ├── lib/
│   │   ├── api.ts             # TanStack Query hooks
│   │   └── xlsx.ts            # SheetJS export logic
│   └── package.json
│
├── backend/                   # FastAPI app
│   ├── main.py                # App entrypoint, router registration
│   ├── routers/
│   │   ├── chat.py            # POST /chat — SSE streaming endpoint
│   │   ├── upload.py          # POST /upload — save to disk + parse trigger
│   │   └── tables.py          # POST /extract-tables — returns JSON
│   ├── services/
│   │   ├── rag.py             # Chunking, Qwen embedding, FAISS retrieval
│   │   ├── openai_client.py   # Wrapper around OpenAI SDK (GPT-4o)
│   │   ├── pdf_parser.py      # PyMuPDF primary parser + Rust fallback logic
│   │   ├── ocr.py             # GLM-OCR-MLX runner, caches output to disk
│   │   └── cache.py           # DiskCache setup and singleton
│   └── pyproject.toml         # uv project config
│
├── data/                      # Local storage (gitignored)
│   ├── pdfs/
│   ├── faiss/
│   ├── cache/
│   └── ocr_output/
│
├── CLAUDE.md                  # ← this file
└── .gitignore                 # must include /data/
```

---

## Implementation Rules

### General

- Always use `async/await` everywhere — no blocking calls on the hot path
- All secrets via environment variables, never hardcoded
- Log errors with context (include file hash, endpoint, model used)
- All endpoints return typed responses — use Pydantic models (backend) and TypeScript interfaces (frontend)
- The `./data/` directory and all subdirs must be created on first run if missing; never fail on absent dirs

### Frontend

- PDF Web Worker **must** be configured — never render PDF on main thread
- Use `useChat` from Vercel AI SDK for the chat panel, do not roll a custom stream parser
- TanStack Query for all server state — no raw `useEffect` + `fetch` patterns
- SheetJS export runs entirely client-side; do not POST table data back to server for download

### Backend (Python)

- Use `uv` for all dependency management:

  ```bash
  uv add openai fastapi pymupdf langchain langchain-community faiss-cpu diskcache mlx-lm
  uv run fastapi dev main.py
  ```

- Streaming chat endpoint must use `StreamingResponse` with `text/event-stream`
- Before calling OpenAI API, always check DiskCache for existing PDF chunks (key: `chunks:{sha256}`)
- Use OpenAI `tool_use` for table extraction — do not parse tables from raw text with regex
- DiskCache instance is a **singleton** initialized at startup in `services/cache.py`

### PDF Parsing Decision Tree

```
PDF uploaded
     │
     ▼
Is it a scanned/image PDF? ──► YES ──► GLM-OCR-MLX → cache text to ocr_output/
     │
     NO
     │
     ▼
File size > 10MB or complex layout?
     │
  YES ──► Rust pdf_engine (lopdf/pdfium) → fast coordinate extraction
     │
     NO
     ▼
PyMuPDF (fitz) ──► primary parser for standard PDFs
```

### Embeddings & RAG

- Embeddings are generated locally using **mlx-lm with Qwen** — never sent to OpenAI
- FAISS index is created per `file_id` and persisted to `./data/faiss/{file_id}.index`
- On chat query: embed user question with Qwen → retrieve top-k chunks from FAISS → inject into GPT-4o context
- Chunk size: 512 tokens, overlap: 64 tokens
- If FAISS index already exists for a `file_id`, load from disk — never re-embed

### OCR

- GLM-OCR-MLX runs **locally** via subprocess or Python binding
- OCR output is cached as plain text in `./data/ocr_output/{file_id}.txt`
- If cached OCR text exists, skip re-running the model entirely
- OCR is only triggered when PyMuPDF returns empty or near-empty text extraction

### OpenAI API Usage

- Model: `gpt-4o` (always, unless explicitly told otherwise)
- Max tokens: `1024` for chat
- Always stream chat responses — never wait for full completion

---

## Environment Variables

### Frontend (`.env.local`)

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (`.env`)

```
OPENAI_API_KEY=sk-...
DATA_DIR=./data
PDF_DIR=./data/pdfs
FAISS_DIR=./data/faiss
CACHE_DIR=./data/cache
OCR_OUTPUT_DIR=./data/ocr_output
QWEN_MODEL_ID=Qwen/Qwen1.5-0.5B          # or preferred Qwen embedding variant
GLM_OCR_MODEL_PATH=./models/glm-ocr-mlx  # local model path
```

---

## Key API Contracts

### `POST /upload`

```typescript
// Request: multipart/form-data, field "file" = PDF
// Response:
{ file_id: string, page_count: number, size_bytes: number, needs_ocr: boolean }
```

### `POST /chat` (SSE)

```typescript
// Request:
{ file_id: string, messages: { role: "user" | "assistant", content: string }[] }
// Response: text/event-stream (Vercel AI SDK compatible)
```

### `POST /extract-tables`

```typescript
// Request:
{ file_id: string, page?: number }  // page = null means all pages
// Response:
{
  tables: {
    title?: string,
    headers: string[],
    rows: string[][]
  }[]
}
```

### `POST /ocr`

```typescript
// Request:
{ file_id: string }
// Response:
{ file_id: string, text: string, cached: boolean }
```

---

## Performance Rules

| Concern | Rule |
|---|---|
| Same PDF uploaded twice | Cache chunks by SHA-256 with DiskCache; skip re-parsing |
| PDF, standard layout | PyMuPDF is sufficient, skip Rust overhead |
| Scanned/image PDF | Trigger GLM-OCR-MLX; cache result to disk |
| FAISS index exists on disk | Load from disk, never re-embed |
| Chat response | Always stream, never block |
| Excel | SheetJS client-side is sufficient |
| Qwen embeddings | Run locally via mlx-lm; never call an external embedding API |

---

## Development Setup

```bash
# 1. Create local data directories
mkdir -p data/pdfs data/faiss data/cache data/ocr_output

# 2. Backend
cd backend
uv sync
uv run fastapi dev main.py

# 3. Frontend
cd frontend
npm install
npm run dev
```

> No Docker or external services required. The app is fully self-contained.

---

## Out of Scope (Do Not Implement)

- User authentication (add later)
- Any cloud storage, cloud cache, or external APIs beyond OpenAI (this is local-first)
- Multi-tenant isolation (add later)
- Mobile layout (desktop-first for now)
- External embedding APIs (Qwen via mlx-lm is the only embedder, always local)
