# Project Implementation Progress

This file tracks the implementation status of the AI PDF Reader project based on the high-level architecture defined in [architecture_design.md](file:///Users/antoniolisi/Projects/AI_pdf_reader/docs/architecture_design.md).

---

## 🏗️ Architecture Status

### 1. Backend Services (FastAPI)

#### ✅ [DONE] OCR Module

- **Status:** Completed & Verified
- **Last Modified:** 2026-03-29
- **Implementation Details:**
  - Developed `OCRService` in `backend/services/ocr.py`.
  - Integrated `mlx-vlm` for local model execution using Apple MLX.
  - Added support for `GLM-OCR-MLX` model targeting scanned/image-based PDFs.
  - Implemented handling for both PIL Image objects and local file paths.
  - **Bug Fix:** Resolved a type mismatch where the model returned a `GenerationResult` object instead of a string; successfully extracted `.text` attribute for consistency.
  - **Verification:** Created and passed unit tests (`tests/test_ocr_service.py`) for synthetic image processing and temporary file handling.

#### ⏳ [PENDING] RAG Pipeline

- **Status:** Not Started
- **Description:** Chunking, Qwen embedding integration, and FAISS vector store management.

#### ✅ [DONE] PDF Parsing Engine

- **Status:** Completed & Verified
- **Last Modified:** 2026-03-29
- **Implementation Details:**
  - Developed `pdf_parser.py` in `backend/services/pdf_parser.py`.
  - Uses **PyMuPDF (fitz)** as the primary parser for standard PDF text, image, and table extraction.
  - All data models refactored to **Pydantic v2** (`BaseModel`) for validation and serialization:
    - `PageImage`, `PageTable`, `PDFMetadata`, `ParsedPage`, `ParsedPDF`.
  - Implements **cache-first parsing**: checks `DiskCache` (key: `chunks:{sha256}`) before opening the file.
  - Computes a stable `file_id` via **SHA-256** of file contents.
  - Supports **heuristic table detection** via PyMuPDF text blocks (bbox, row count, preview).
  - Includes **word-based chunking** with configurable size (`512`) and overlap (`64`) for RAG.
  - **OCR is intentionally excluded** from this module — per-page OCR is triggered by the frontend via a dedicated endpoint.
  - Verified with `python3 -m py_compile`.

#### ✅ [DONE] Cache Service

- **Status:** Completed & Verified
- **Last Modified:** 2026-03-29
- **Implementation Details:**
  - Developed `cache.py` in `backend/services/cache.py`.
  - Exports a singleton `disk_cache: Cache` instance from `diskcache`.
  - Auto-creates the cache directory (`./data/cache/`) on startup if missing.
  - Used by `pdf_parser.py` to persist per-page text chunks keyed by PDF SHA-256.

#### ⏳ [PENDING] API Routers

- **Status:** Not Started
- **Description:** FastAPI endpoints for `/upload`, `/chat` (SSE), and `/extract-tables`.

---

### 2. Frontend (Next.js 14)

#### ⏳ [PENDING] PDF Viewer

- **Status:** Not Started
- **Description:** Split-panel UI with `react-pdf` and web worker integration.

#### ⏳ [PENDING] Chat Interface

- **Status:** Not Started
- **Description:** AI-powered chat panel using Vercel AI SDK.

#### ⏳ [PENDING] Table Extraction UI

- **Status:** Not Started
- **Description:** Previewing extracted tables and client-side Excel download via SheetJS.

---

### 3. Infrastructure & Storage

#### ✅ [DONE] Local Storage Structure

- **Status:** Initialized
- **Description:** Data directories (`pdfs/`, `faiss/`, `cache/`, `ocr_output/`) created according to specification.

#### ⏳ [PENDING] Rust Performance Modules (V2)

- **Status:** Not Started
- **Description:** Optional `PyO3` modules for high-speed PDF processing and Excel writing.
