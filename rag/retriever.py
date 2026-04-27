"""Thin wrapper around :class:`ChromaStore` that exposes a top-k retrieval API."""

from __future__ import annotations

from typing import Dict, List

from .vector_store import ChromaStore


class Retriever:
    """Thin wrapper around ChromaStore.query -- returns the top-K hits as a structured list."""

    def __init__(self, store: ChromaStore) -> None:
        self.store = store

    def top_k(self, query: str, k: int = 5) -> List[Dict]:
        """Return the top-k retrieved chunks. Same shape as ChromaStore.query."""
        return self.store.query(query, k=k)
