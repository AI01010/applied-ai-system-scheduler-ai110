"""Persistent ChromaDB-backed vector store for the PawPal knowledge base.

Responsibilities:
    * Read every ``*.md`` file in ``data/knowledge_base/``.
    * Strip and parse a simple ``---`` YAML frontmatter block (no PyYAML needed).
    * Chunk each document by paragraph, splitting long paragraphs on sentence
      boundaries so no single chunk exceeds ~1000 characters.
    * Embed the chunks with our local :class:`Embedder` and upsert into a
      persistent Chroma collection rooted at ``./data/chroma``.
    * Expose a ``query`` method that returns ranked hits with cosine similarity
      scores in the [0, 1] range.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .embedder import Embedder


# Approximate character cap per chunk -- ~200 tokens at ~5 chars/token.
_MAX_CHUNK_CHARS = 1000


def _parse_frontmatter(raw: str) -> Tuple[Dict[str, str], str]:
    """Parse a leading ``---\\nkey: value\\n---`` block.

    Returns (metadata_dict, body). If no frontmatter is present, returns
    ({}, raw).
    """
    if not raw.startswith("---"):
        return {}, raw

    # Match an opening ---, the body, and a closing --- on its own line.
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", raw, re.DOTALL)
    if not match:
        return {}, raw

    block = match.group(1)
    body = raw[match.end():]

    metadata: Dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, body


def _split_long_paragraph(paragraph: str, max_chars: int = _MAX_CHUNK_CHARS) -> List[str]:
    """Break a paragraph into sentence-aligned pieces under ``max_chars``."""
    if len(paragraph) <= max_chars:
        return [paragraph]

    # Naive sentence splitter: break on '. ', '! ', '? ' while keeping punctuation.
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    chunks: List[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        candidate = (current + " " + sentence).strip() if current else sentence
        if len(candidate) > max_chars and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current.strip())
    return chunks


def _chunk_text(body: str) -> List[str]:
    """Chunk a markdown body by paragraph, splitting long paragraphs further."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    chunks: List[str] = []
    for paragraph in paragraphs:
        chunks.extend(_split_long_paragraph(paragraph))
    return chunks


class ChromaStore:
    """Persistent ChromaDB collection rooted at ``./data/chroma/``."""

    COLLECTION_NAME = "pawpal_kb"
    PERSIST_DIR = "./data/chroma"

    def __init__(self, embedder: Optional[Embedder] = None) -> None:
        # Lazy import so test environments without chromadb can still import this module.
        import chromadb

        os.makedirs(self.PERSIST_DIR, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self.PERSIST_DIR)
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self.embedder = embedder or Embedder()

    # ----- ingestion -------------------------------------------------------

    def ingest_knowledge_base(
        self,
        kb_dir: str = "./data/knowledge_base",
        force_rebuild: bool = False,
    ) -> int:
        """Read every ``.md`` file, parse, chunk, embed, and upsert.

        If the collection is already populated and ``force_rebuild`` is False,
        this is a no-op and returns the existing document count.

        Returns:
            The total number of chunks now stored in the collection.
        """
        if force_rebuild:
            self.reset()

        existing = self.count()
        if existing > 0 and not force_rebuild:
            return existing

        kb_path = Path(kb_dir)
        if not kb_path.exists():
            return self.count()

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, str]] = []

        for md_path in sorted(kb_path.glob("*.md")):
            raw = md_path.read_text(encoding="utf-8")
            frontmatter, body = _parse_frontmatter(raw)
            chunks = _chunk_text(body)
            stem = md_path.stem
            source = md_path.name

            for idx, chunk in enumerate(chunks):
                chunk_id = f"{stem}__{idx}"
                meta = {
                    "source": source,
                    "chunk_index": idx,
                }
                # Only include scalar (str/int/float/bool) values from frontmatter --
                # Chroma will reject anything else.
                for k, v in frontmatter.items():
                    if isinstance(v, (str, int, float, bool)):
                        meta[k] = v
                ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append(meta)

        if not documents:
            return self.count()

        embeddings = self.embedder.encode(documents)
        # Upsert so re-runs with the same IDs don't error.
        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return self.count()

    # ----- query -----------------------------------------------------------

    def query(self, text: str, k: int = 5) -> List[Dict]:
        """Return the top-k chunks for ``text``, sorted by similarity desc.

        Each hit is a dict with keys: ``text``, ``score`` (in [0, 1]),
        ``metadata``, and ``source``.
        """
        if not text or k <= 0:
            return []
        if self.count() == 0:
            return []

        query_embedding = self.embedder.encode_one(text)
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]

        hits: List[Dict] = []
        for doc, meta, dist in zip(docs, metas, dists):
            # cosine distance in Chroma is 1 - cosine_sim; clip to [0, 1].
            score = 1.0 - float(dist)
            if score < 0.0:
                score = 0.0
            elif score > 1.0:
                score = 1.0
            meta = dict(meta or {})
            hits.append(
                {
                    "text": doc,
                    "score": score,
                    "metadata": meta,
                    "source": meta.get("source", ""),
                }
            )
        # Already sorted by Chroma (ascending distance == descending score),
        # but sort defensively to honor the docstring contract.
        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits

    # ----- bookkeeping -----------------------------------------------------

    def count(self) -> int:
        """Return the number of chunks currently stored."""
        try:
            return int(self._collection.count())
        except Exception:
            return 0

    def reset(self) -> None:
        """Delete and recreate the collection, dropping all chunks."""
        try:
            self._client.delete_collection(self.COLLECTION_NAME)
        except Exception:
            # If the collection doesn't exist yet, that's fine.
            pass
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
