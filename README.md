# AI PDF Reader & Chat

A local-first, performant web application that allows users to seamlessly upload, view, chat with, and extract tables from PDFs. Everything runs locally on the user's machine, ensuring maximum privacy without cloud dependencies.

## Key Features

- **PDF Viewer & Chat**: Split-panel UI with a high-performance PDF viewer and an AI-powered chat interface.
- **Table Extraction**: Automatically extract and download PDF tables as `.xlsx` spreadsheets.
- **Local OCR**: Built-in support for scanning and reading image-based PDFs locally using GLM-OCR-MLX.
- **Local Vectors & RAG**: Uses Apple MLX for local embeddings and FAISS for fast local vector search.

## Tech Stack

- **Frontend**: Next.js 14+ (App Router), TypeScript, TailwindCSS, shadcn/ui.
- **Backend**: FastAPI (Python 3.12+), `uv` package manager, LangChain, FAISS.
- **AI/ML**: Vercel AI SDK, OpenAI SDK (for GPT-4o chat), `mlx-lm` local embeddings, `GLM-OCR-MLX`.
- **High-Performance Extractors**: Optional Rust endpoints via PyO3 for ultra-fast PDF operations.

## Architecture

See `docs/architecture_design.md` for our complete architecture, development setup, and implementation rules.

## Structure

- `/frontend/` - Next.js web application
- `/backend/` - FastAPI application and AI routing
- `/data/` - Local filesystem storage for PDFs, vectors, and OCR extractions

## Getting Started

1. Create the `data` directories (`mkdir -p data/pdfs data/faiss data/cache data/ocr_output`).
2. Run backend: Navigate to `backend`, sync dependencies with `uv`, and start FastAPI main runner.
3. Run frontend: Navigate to `frontend`, run `npm install`, then `npm run dev`.
4. Ensure `.env` files are configured appropriately for OpenAI and local paths.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
