"""
DiskCache Service

Singleton wrapper around diskcache.Cache for persistent,
fast key-value storage of chunks, embeddings, and metadata.
"""

import os
from pathlib import Path

from diskcache import Cache

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
CACHE_DIR = Path(os.getenv("CACHE_DIR", DATA_DIR / "cache"))

# Ensure directory exists on first use
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

disk_cache: Cache = Cache(str(CACHE_DIR))
"""Global DiskCache instance. Use this throughout the backend."""
