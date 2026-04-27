"""Local sentence-transformers embedder.

Wraps ``sentence-transformers/all-MiniLM-L6-v2`` (384-dim, cosine-friendly).
The actual model object is lazy-loaded on first use so that ``import rag.embedder``
stays cheap and the module is importable in environments where the heavy ML
dependency isn't installed (unit tests can mock the encode methods).
"""

from __future__ import annotations

from typing import List, Optional


class Embedder:
    """Wraps sentence-transformers/all-MiniLM-L6-v2 -- local, 384-dim."""

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    DIM = 384

    def __init__(self) -> None:
        # Lazy: don't load the model until the first encode call.
        self._model: Optional[object] = None

    def _ensure_model(self) -> object:
        """Load the SentenceTransformer model on first use and cache it."""
        if self._model is None:
            # Lazy import so importing this module doesn't require the dep.
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.MODEL_NAME)
        return self._model

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of strings. Returns a list of 384-float vectors."""
        if not texts:
            return []
        model = self._ensure_model()
        vectors = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        # SentenceTransformer returns numpy arrays; convert to plain lists for Chroma.
        return [vec.tolist() for vec in vectors]

    def encode_one(self, text: str) -> List[float]:
        """Embed a single string. Returns a 384-float vector."""
        return self.encode([text])[0]
