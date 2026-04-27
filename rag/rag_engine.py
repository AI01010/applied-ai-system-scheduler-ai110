"""RAG orchestrator: feature_builder -> retriever -> LLM (or template) -> Recommendation.

The engine takes an ``Owner`` and a target ``Pet``, builds a natural-language query,
retrieves the top-K most relevant knowledge-base chunks via :class:`ChromaStore`,
then either:

* calls Anthropic Claude with the chunks as ``<context>`` and asks for a JSON
  schedule (the "RAG path"), or
* falls back to a deterministic template that emits a sensible default schedule
  for the pet's species + energy level (when no API key is set or the LLM call
  fails).

Either path produces a :class:`Recommendation` carrying proposed tasks,
explanation, citations, confidence, and a flag indicating which path was used.
Every call appends a structured JSON line to ``logs/rag.log`` for auditability.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .feature_builder import build_query
from .retriever import Retriever
from .vector_store import ChromaStore


# Phrases that trigger the medical-advice guardrail. Matched case-insensitive,
# whole-word so "diagnostic tests" doesn't fire on "diagnose".
_MEDICAL_DENY_PATTERNS = [
    r"\bdiagnos(e|is|ing|ed|tic)\b",
    r"\bprescrib(e|es|ing|ed)\b",
    r"\bcure(s|d)?\b",
    r"\bdosage\b",
    r"\bmedication dose\b",
]

_LOG_PATH = Path("./logs/rag.log")
_DEFAULT_MODEL = "claude-sonnet-4-6"


# ── Recommendation dataclass ──────────────────────────────────────────────────


@dataclass
class Recommendation:
    """The output of a single RAG generation call."""

    proposed_tasks: List[dict] = field(default_factory=list)
    explanation: str = ""
    citations: List[str] = field(default_factory=list)
    confidence: float = 0.0
    used_llm: bool = False
    retrieval_hits: List[dict] = field(default_factory=list)


# ── Guardrails ────────────────────────────────────────────────────────────────


def _scrub_medical_claims(text: str) -> tuple[str, bool]:
    """Replace medical-claim sentences with a 'consult your vet' note.

    Returns the (scrubbed_text, was_scrubbed) tuple.
    """
    if not text:
        return text, False
    scrubbed = text
    triggered = False
    for pattern in _MEDICAL_DENY_PATTERNS:
        if re.search(pattern, scrubbed, flags=re.IGNORECASE):
            triggered = True
            break
    if triggered:
        scrubbed = (
            text + "\n\n[Guardrail] Some medical-sounding language was flagged. "
            "PawPal+ AI is advisory only — please consult your veterinarian for "
            "anything health-related."
        )
    return scrubbed, triggered


# ── LLM prompt scaffolding ────────────────────────────────────────────────────


_SYSTEM_PROMPT = (
    "You are PawPal+ AI, a pet care scheduling assistant. "
    "Be concrete with HH:MM times. "
    "Only suggest tasks supported by the provided context. "
    "Cite sources by filename in each task's rationale field. "
    "Never give medical diagnoses or specific medication dosages — "
    "if asked anything medical, say 'Consult your veterinarian.' "
    "Output STRICT JSON only, no prose, no markdown fences."
)


def _build_user_prompt(query: str, hits: List[dict]) -> str:
    """Format the query + retrieved context + JSON schema instruction."""
    context_lines = []
    for i, hit in enumerate(hits, start=1):
        source = hit.get("source", "unknown")
        score = hit.get("score", 0.0)
        text = (hit.get("text") or "").strip()
        context_lines.append(f"[{i}] (source: {source}, score: {score:.2f})\n{text}")
    context_block = "\n\n".join(context_lines) if context_lines else "(no context retrieved)"

    return (
        f"Query: {query}\n\n"
        f"<context>\n{context_block}\n</context>\n\n"
        "Based on the context above, propose 3-6 daily care tasks. Respond with JSON in this exact shape:\n"
        "{\n"
        '  "proposed_tasks": [\n'
        '    {"title": str, "time": "HH:MM", "duration_minutes": int, "priority": "low"|"medium"|"high", "rationale": str},\n'
        "    ...\n"
        "  ],\n"
        '  "explanation": "1-2 sentences summarizing the schedule",\n'
        '  "citations": ["source_filename.md", ...]\n'
        "}\n"
        "Each rationale should reference one or more source filenames from the context."
    )


def _call_anthropic(query: str, hits: List[dict], model: str) -> Optional[dict]:
    """Call Claude. Return parsed JSON dict, or None on any failure."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        # Lazy import: keep this module importable in environments without the SDK.
        from anthropic import Anthropic  # type: ignore

        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(query, hits)}],
        )
        # response.content is a list of content blocks; first one is text.
        text_blocks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
        if not text_blocks:
            return None
        raw = text_blocks[0].strip()
        # Defensive JSON extraction: strip markdown fences if Claude added them.
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
        return json.loads(raw)
    except Exception:
        return None


# ── Deterministic fallback ────────────────────────────────────────────────────


def _fallback_template(pet, hits: List[dict]) -> dict:
    """Return a sensible default schedule when the LLM is unavailable.

    Built from the pet's species + energy level. Citations come from whatever
    the retriever returned, so the user still sees grounded sources.
    """
    species = (getattr(pet, "species", "other") or "other").lower()
    energy = (getattr(pet, "energy", "medium") or "medium").lower()

    if species == "dog":
        if energy == "high":
            tasks = [
                {"title": "Morning walk",   "time": "07:30", "duration_minutes": 40, "priority": "high",   "rationale": "High-energy dogs need a long morning walk to start the day."},
                {"title": "Midday play",    "time": "12:30", "duration_minutes": 20, "priority": "medium", "rationale": "Short play break breaks up the day for high-energy dogs."},
                {"title": "Evening walk",   "time": "18:00", "duration_minutes": 45, "priority": "high",   "rationale": "Second exercise window before bed prevents restlessness."},
                {"title": "Feeding",        "time": "08:30", "duration_minutes": 10, "priority": "high",   "rationale": "Morning meal after the walk."},
                {"title": "Feeding",        "time": "18:45", "duration_minutes": 10, "priority": "high",   "rationale": "Evening meal after the walk."},
            ]
        elif energy == "low":
            tasks = [
                {"title": "Short walk",  "time": "08:00", "duration_minutes": 15, "priority": "medium", "rationale": "Low-energy dogs benefit from a brief gentle walk."},
                {"title": "Feeding",     "time": "08:30", "duration_minutes": 10, "priority": "high",   "rationale": "Morning meal."},
                {"title": "Light play",  "time": "15:00", "duration_minutes": 10, "priority": "low",    "rationale": "Light enrichment for low-energy dogs."},
                {"title": "Feeding",     "time": "18:00", "duration_minutes": 10, "priority": "high",   "rationale": "Evening meal."},
            ]
        else:
            tasks = [
                {"title": "Morning walk", "time": "07:30", "duration_minutes": 25, "priority": "high",   "rationale": "Standard morning walk."},
                {"title": "Feeding",      "time": "08:00", "duration_minutes": 10, "priority": "high",   "rationale": "Morning meal."},
                {"title": "Evening walk", "time": "18:00", "duration_minutes": 25, "priority": "high",   "rationale": "Evening walk."},
                {"title": "Feeding",      "time": "18:30", "duration_minutes": 10, "priority": "high",   "rationale": "Evening meal."},
            ]
    elif species == "cat":
        tasks = [
            {"title": "Feeding",        "time": "07:30", "duration_minutes": 10, "priority": "high",   "rationale": "Morning meal."},
            {"title": "Play session",   "time": "10:00", "duration_minutes": 15, "priority": "medium", "rationale": "Indoor enrichment to prevent boredom."},
            {"title": "Litter check",   "time": "15:00", "duration_minutes": 5,  "priority": "medium", "rationale": "Mid-day litter scoop."},
            {"title": "Feeding",        "time": "18:00", "duration_minutes": 10, "priority": "high",   "rationale": "Evening meal."},
            {"title": "Evening play",   "time": "19:30", "duration_minutes": 15, "priority": "low",    "rationale": "Wind-down play to settle for the night."},
        ]
    else:
        tasks = [
            {"title": "Feeding",       "time": "08:00", "duration_minutes": 10, "priority": "high",   "rationale": "Morning meal."},
            {"title": "Habitat check", "time": "12:00", "duration_minutes": 10, "priority": "medium", "rationale": "Mid-day welfare check."},
            {"title": "Feeding",       "time": "18:00", "duration_minutes": 10, "priority": "high",   "rationale": "Evening meal."},
        ]

    citations = list({h.get("source", "") for h in hits if h.get("source")})
    return {
        "proposed_tasks": tasks,
        "explanation": (
            f"Default schedule for a {energy}-energy {species}. LLM was not called "
            "(no API key or call failed); recommendations are template-driven and "
            "grounded in the retrieved knowledge-base chunks listed in citations."
        ),
        "citations": citations,
    }


# ── Logging ───────────────────────────────────────────────────────────────────


def _log_event(query: str, hits: List[dict], rec: Recommendation) -> None:
    """Append a structured JSON line to logs/rag.log."""
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "query": query,
            "top_k": [
                {
                    "source": h.get("source"),
                    "score": round(float(h.get("score", 0.0)), 4),
                    "snippet": (h.get("text") or "")[:120],
                }
                for h in hits
            ],
            "used_llm": rec.used_llm,
            "confidence": round(rec.confidence, 4),
            "proposed_count": len(rec.proposed_tasks),
            "citations": rec.citations,
        }
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception:
        # Never let logging crash the pipeline.
        pass


# ── Public engine ─────────────────────────────────────────────────────────────


class RAGEngine:
    """Orchestrates the retrieve -> generate -> guardrail -> log flow."""

    def __init__(
        self,
        store: Optional[ChromaStore] = None,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        # Lazy: load .env if python-dotenv is around, but don't fail without it.
        try:
            from dotenv import load_dotenv  # type: ignore

            load_dotenv()
        except Exception:
            pass

        self.store = store if store is not None else ChromaStore()
        self.retriever = Retriever(self.store)
        self.model = model

    def generate(self, owner, pet, k: int = 5) -> Recommendation:
        """Run the full RAG pipeline for a single (owner, pet) pair."""
        query = build_query(owner, pet)
        hits = self.retriever.top_k(query, k=k) if self.store.count() > 0 else []

        # Try the LLM first; fall back to the deterministic template.
        llm_result = _call_anthropic(query, hits, self.model) if hits else None
        used_llm = llm_result is not None

        if llm_result is None:
            payload = _fallback_template(pet, hits)
        else:
            # Defensive: ensure required keys exist with sane defaults.
            payload = {
                "proposed_tasks": llm_result.get("proposed_tasks", []) or [],
                "explanation":   llm_result.get("explanation", "") or "",
                "citations":     llm_result.get("citations", []) or [],
            }
            # Backfill citations from retrieved sources if the LLM forgot.
            if not payload["citations"]:
                payload["citations"] = list({h.get("source", "") for h in hits if h.get("source")})

        # Confidence (this layer): average top-K similarity. The recommender
        # layer refines it with constraint-pass-rate downstream.
        if hits:
            avg_sim = sum(float(h.get("score", 0.0)) for h in hits) / len(hits)
        else:
            avg_sim = 0.0

        # Guardrail scrub on the explanation + each rationale.
        explanation, scrubbed = _scrub_medical_claims(payload["explanation"])
        for task in payload["proposed_tasks"]:
            if isinstance(task, dict) and "rationale" in task:
                task["rationale"], _ = _scrub_medical_claims(task["rationale"])

        rec = Recommendation(
            proposed_tasks=payload["proposed_tasks"],
            explanation=explanation,
            citations=payload["citations"],
            confidence=avg_sim,
            used_llm=used_llm,
            retrieval_hits=hits,
        )

        _log_event(query, hits, rec)
        return rec
