"""Tests for the RAG layer.

The "live" tests (embedder, vector store, end-to-end retrieval) are gated by an
environment variable so the suite can run quickly without downloading the
sentence-transformers model. Set ``RUN_RAG_LIVE_TESTS=1`` to enable them.

Default tests cover pure-Python pieces: feature_builder, frontmatter parsing,
chunking, prompt formatting, the deterministic-fallback path of the engine, and
the medical-claim guardrail.
"""

import os
from types import SimpleNamespace

import pytest

from rag.feature_builder import build_query
from rag.rag_engine import (
    Recommendation,
    _build_user_prompt,
    _fallback_template,
    _scrub_medical_claims,
)
from rag.vector_store import _chunk_text, _parse_frontmatter

RUN_LIVE = os.environ.get("RUN_RAG_LIVE_TESTS") == "1"


# ── feature_builder ───────────────────────────────────────────────────────────


def _make_owner_pet():
    pet = SimpleNamespace(
        name="Mochi", species="dog", age=3, energy="high", health_notes="",
        tasks=[SimpleNamespace(title="Walk", time="08:00")],
    )
    owner = SimpleNamespace(
        name="Jordan",
        contact_info="",
        busy_times=[("09:00", "17:00")],
    )
    return owner, pet


def test_build_query_includes_signal_words():
    owner, pet = _make_owner_pet()
    q = build_query(owner, pet)
    # Each signal must be in the query string so the embedding has signal.
    assert "dog" in q.lower()
    assert "high" in q.lower()
    assert "mochi" in q.lower()
    assert "09:00-17:00" in q
    assert "walk" in q.lower()


def test_build_query_handles_missing_fields():
    owner = SimpleNamespace(busy_times=None)
    pet = SimpleNamespace()
    q = build_query(owner, pet)
    assert isinstance(q, str) and len(q) > 0


# ── frontmatter parsing ───────────────────────────────────────────────────────


def test_parse_frontmatter_extracts_kv():
    raw = "---\ntopic: feeding\npet_type: dog\n---\nBody here."
    meta, body = _parse_frontmatter(raw)
    assert meta == {"topic": "feeding", "pet_type": "dog"}
    assert body.strip() == "Body here."


def test_parse_frontmatter_no_block():
    raw = "Just a body, no frontmatter."
    meta, body = _parse_frontmatter(raw)
    assert meta == {}
    assert body == raw


# ── chunking ──────────────────────────────────────────────────────────────────


def test_chunk_text_splits_paragraphs():
    body = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = _chunk_text(body)
    assert len(chunks) == 3
    assert chunks[0] == "First paragraph."


def test_chunk_text_splits_long_paragraph_on_sentences():
    long_para = "Sentence one. " * 200  # ~3000 chars, will exceed the per-chunk cap
    chunks = _chunk_text(long_para)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 1100  # ~max_chars + a sentence buffer


# ── guardrails ────────────────────────────────────────────────────────────────


def test_scrub_medical_claims_triggers_on_diagnose():
    text = "I will diagnose your dog with arthritis."
    out, was_scrubbed = _scrub_medical_claims(text)
    assert was_scrubbed is True
    assert "veterinarian" in out.lower()


def test_scrub_medical_claims_passes_clean_text():
    text = "Walk your high-energy dog twice a day."
    out, was_scrubbed = _scrub_medical_claims(text)
    assert was_scrubbed is False
    assert out == text


# ── prompt construction ──────────────────────────────────────────────────────


def test_build_user_prompt_embeds_context():
    hits = [
        {"text": "High-energy dogs need 60+ min daily.", "source": "dog_high_energy.md", "score": 0.81},
        {"text": "Avoid post-meal exercise.",            "source": "health_post_meal.md",   "score": 0.65},
    ]
    prompt = _build_user_prompt("schedule for high-energy dog", hits)
    assert "dog_high_energy.md" in prompt
    assert "0.81" in prompt
    assert "<context>" in prompt and "</context>" in prompt
    assert "JSON" in prompt


# ── deterministic fallback ────────────────────────────────────────────────────


def test_fallback_template_dog_high():
    pet = SimpleNamespace(species="dog", energy="high")
    out = _fallback_template(pet, hits=[{"source": "dog_high_energy.md"}])
    assert "proposed_tasks" in out
    assert any("walk" in t["title"].lower() for t in out["proposed_tasks"])
    assert "dog_high_energy.md" in out["citations"]


def test_fallback_template_cat():
    pet = SimpleNamespace(species="cat", energy="medium")
    out = _fallback_template(pet, hits=[])
    titles = [t["title"].lower() for t in out["proposed_tasks"]]
    assert any("feeding" in t for t in titles)


def test_fallback_template_unknown_species():
    pet = SimpleNamespace(species="lizard", energy="low")
    out = _fallback_template(pet, hits=[])
    assert len(out["proposed_tasks"]) >= 2


# ── Recommendation dataclass ──────────────────────────────────────────────────


def test_recommendation_default_fields():
    rec = Recommendation()
    assert rec.proposed_tasks == []
    assert rec.citations == []
    assert rec.confidence == 0.0
    assert rec.used_llm is False
    assert rec.retrieval_hits == []


# ── live tests (only when RUN_RAG_LIVE_TESTS=1) ──────────────────────────────


@pytest.mark.skipif(not RUN_LIVE, reason="set RUN_RAG_LIVE_TESTS=1 to run")
def test_embedder_shape():
    from rag.embedder import Embedder

    embedder = Embedder()
    vec = embedder.encode_one("Hello, world.")
    assert isinstance(vec, list)
    assert len(vec) == Embedder.DIM


@pytest.mark.skipif(not RUN_LIVE, reason="set RUN_RAG_LIVE_TESTS=1 to run")
def test_chroma_ingest_and_query_roundtrip(tmp_path, monkeypatch):
    """Ingest a tiny KB and verify retrieval returns it."""
    from rag.vector_store import ChromaStore

    # Override the persistence path so we don't pollute the real store.
    monkeypatch.setattr(ChromaStore, "PERSIST_DIR", str(tmp_path / "chroma"))

    # Minimal KB on disk
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "doc.md").write_text(
        "---\ntopic: feeding\npet_type: dog\n---\n"
        "High-energy dogs need 60-minute walks twice a day.",
        encoding="utf-8",
    )

    store = ChromaStore()
    n = store.ingest_knowledge_base(kb_dir=str(kb), force_rebuild=True)
    assert n >= 1

    hits = store.query("schedule for an energetic dog", k=3)
    assert len(hits) >= 1
    assert hits[0]["score"] > 0
    assert "dog" in hits[0]["text"].lower()
