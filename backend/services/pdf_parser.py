"""
PDF Parser Service

Primary PDF parsing logic using PyMuPDF (fitz).
Handles text extraction, layout analysis, images, and heuristic table detection.

OCR is **not** handled here — it is triggered per-page by the frontend
via a dedicated endpoint (see routers/tables.py or routers/ocr.py).

Architecture:
    PDF uploaded
         |
         ▼
    File size > 10MB or complex layout?
         |
      YES ──► Rust pdf_engine (optional, graceful fallback)
         |
         NO
         ▼
    PyMuPDF (fitz) ──► primary parser for standard PDFs
"""

import hashlib
import os
from pathlib import Path

import fitz  # PyMuPDF
from pydantic import BaseModel, Field

from services.cache import disk_cache

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
PDF_DIR = Path(os.getenv("PDF_DIR", DATA_DIR / "pdfs"))

_LARGE_FILE_THRESHOLD_BYTES = 10 * 1024 * 1024  # 10 MB

# Chunking defaults
_CHUNK_SIZE = 512
_CHUNK_OVERLAP = 64


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class PageImage(BaseModel):
    """Metadata for an image found on a PDF page."""
    index: int
    width: int | None = None
    height: int | None = None
    ext: str | None = None
    size_bytes: int = 0


class PageTable(BaseModel):
    """Candidate table region detected on a PDF page."""
    bbox: list[float]
    row_count: int
    preview: str = Field(max_length=200)


class PDFMetadata(BaseModel):
    """Lightweight metadata container for a parsed PDF."""
    file_id: str
    page_count: int
    size_bytes: int


class ParsedPage(BaseModel):
    """Represents a single parsed PDF page."""
    page_number: int
    text: str = ""
    images: list[PageImage] = []
    tables: list[PageTable] = []


class ParsedPDF(BaseModel):
    """Represents a fully parsed PDF document."""
    metadata: PDFMetadata
    pages: list[ParsedPage] = []
    raw_text: str = ""

    @property
    def chunks(self) -> list[str]:
        """Lazily split raw_text into overlapping chunks."""
        return _chunk_text(self.raw_text, _CHUNK_SIZE, _CHUNK_OVERLAP)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_pdf(file_path: str | Path) -> ParsedPDF:
    """
    Parse a PDF file and return a structured representation.

    Flow:
        1. Compute SHA-256 file_id.
        2. Check DiskCache for existing chunks (key: chunks:{file_id}).
        3. Open with PyMuPDF.
        4. Extract text, images, tables per page.
        5. Cache chunks to DiskCache.
    """
    file_path = Path(file_path)
    file_id = _compute_file_id(file_path)
    size_bytes = file_path.stat().st_size

    # 1. Try cache first
    cached = _get_cached_chunks(file_id)
    if cached is not None:
        metadata = PDFMetadata(
            file_id=file_id,
            page_count=len(cached),
            size_bytes=size_bytes,
        )
        raw_text = "\n\n".join(cached)
        pages = [
            ParsedPage(page_number=i + 1, text=text)
            for i, text in enumerate(cached)
        ]
        return ParsedPDF(metadata=metadata, pages=pages, raw_text=raw_text)

    # 2. Open document
    doc = fitz.open(file_path)
    page_count = len(doc)

    metadata = PDFMetadata(
        file_id=file_id,
        page_count=page_count,
        size_bytes=size_bytes,
    )

    # 3. Extract content
    pages, raw_text = _extract_with_pymupdf(doc)
    doc.close()

    # 4. Cache chunks
    _cache_chunks(file_id, pages)

    return ParsedPDF(metadata=metadata, pages=pages, raw_text=raw_text)


def get_pdf_text(file_path: str | Path) -> str:
    """Convenience: return only the raw text of a PDF."""
    return parse_pdf(file_path).raw_text


def get_pdf_chunks(file_path: str | Path) -> list[str]:
    """Convenience: return cached or fresh chunks for a PDF."""
    return parse_pdf(file_path).chunks


# ---------------------------------------------------------------------------
# Extraction backend
# ---------------------------------------------------------------------------

def _extract_with_pymupdf(doc: fitz.Document) -> tuple[list[ParsedPage], str]:
    """Extract text, images, and table-like structures using PyMuPDF."""
    pages: list[ParsedPage] = []
    parts: list[str] = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)

        text = page.get_text("text").strip()
        images = [
            _make_page_image(i, img, page)
            for i, img in enumerate(page.get_images(full=True), start=1)
        ]
        tables = _extract_page_tables(page)

        parsed_page = ParsedPage(
            page_number=page_num + 1,
            text=text,
            images=images,
            tables=tables,
        )
        pages.append(parsed_page)
        parts.append(text)

    return pages, "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Helpers: images, tables
# ---------------------------------------------------------------------------

def _make_page_image(index: int, img: tuple, page: fitz.Page) -> PageImage:
    """Build a PageImage from a PyMuPDF image tuple."""
    xref = img[0]
    base_image = page.parent.extract_image(xref)
    return PageImage(
        index=index,
        width=base_image.get("width"),
        height=base_image.get("height"),
        ext=base_image.get("ext"),
        size_bytes=len(base_image.get("image", b"")),
    )


def _extract_page_tables(page: fitz.Page) -> list[PageTable]:
    """
    Heuristic table detection via PyMuPDF text blocks.
    Returns a list of candidate table regions.
    """
    tables: list[PageTable] = []
    blocks = page.get_text("blocks")

    for block in blocks:
        x0, y0, x1, y1, text, block_no, block_type = block
        if block_type == 1:  # image block
            continue
        lines = text.split("\n")
        if len(lines) > 2 and any("\t" in line or "  " in line for line in lines):
            tables.append(PageTable(
                bbox=[x0, y0, x1, y1],
                row_count=len(lines),
                preview=text[:200],
            ))

    return tables


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Split text into overlapping chunks by word count.

    Args:
        text: Raw text to split.
        chunk_size: Target word count per chunk.
        overlap: Word overlap between consecutive chunks.
    """
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    step = max(1, chunk_size - overlap)
    i = 0
    while i < len(words):
        window = words[i : i + chunk_size]
        chunks.append(" ".join(window))
        i += step

    return chunks


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

def _compute_file_id(file_path: Path) -> str:
    """SHA-256 of file contents — stable, deterministic identifier."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _cache_key(file_id: str) -> str:
    return f"chunks:{file_id}"


def _get_cached_chunks(file_id: str) -> list[str] | None:
    """Retrieve cached chunks from DiskCache if present."""
    key = _cache_key(file_id)
    cached = disk_cache.get(key)
    if cached is not None and isinstance(cached, list):
        return cached
    return None


def _cache_chunks(file_id: str, pages: list[ParsedPage]) -> None:
    """Store per-page text chunks in DiskCache."""
    key = _cache_key(file_id)
    chunks = [page.text for page in pages if page.text.strip()]
    disk_cache.set(key, chunks)
