"""Ranking and confidence scoring for the PawPal+ recommender.

Consumes the ``Recommendation`` produced by the RAG layer, validates each
proposed slot against the owner's calendar via
:mod:`recommender.constraint_engine`, scores the survivors, and returns a
unified result dict consumed by the UI / scheduler.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from .constraint_engine import (
    conflicts_with_existing,
    validate_slots,
    violates_busy_times,
)

if TYPE_CHECKING:  # pragma: no cover - import guard, avoids circular dep
    from rag.rag_engine import Recommendation  # noqa: F401


def _clip01(x: float) -> float:
    """Clamp ``x`` into the closed interval ``[0.0, 1.0]``."""
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _avg_similarity(retrieval_hits: Iterable[dict]) -> float:
    """Average ``"similarity"`` across retrieval hits, or 0.0 if none.

    Tolerates hits that are missing the field; non-numeric values are skipped.
    """
    sims: list[float] = []
    for hit in retrieval_hits or []:
        if not isinstance(hit, dict):
            continue
        sim = hit.get("similarity", hit.get("score"))
        try:
            sims.append(float(sim))
        except (TypeError, ValueError):
            continue
    if not sims:
        return 0.0
    return sum(sims) / len(sims)


def slot_score(slot: dict, retrieval_avg_sim: float, satisfied: bool) -> float:
    """Score a single slot.

    ``0.6 * retrieval_avg_sim + 0.4 * (1.0 if satisfied else 0.0)``. The
    ``slot`` argument is accepted for API symmetry / future extension.
    """
    _ = slot  # currently unused, accepted for forward-compat
    sim_component = 0.6 * float(retrieval_avg_sim or 0.0)
    sat_component = 0.4 * (1.0 if satisfied else 0.0)
    return _clip01(sim_component + sat_component)


def rank_slots(
    slots: list[dict],
    retrieval_hits: list[dict],
    busy_times: list[tuple[str, str]],
    existing_tasks: list,
) -> list[dict]:
    """Return ``slots`` sorted by descending score, each carrying a ``"score"`` key.

    A slot is "satisfied" when it does not violate the owner's busy windows
    and does not conflict with any existing task. The retrieval signal is the
    average similarity across ``retrieval_hits``.
    """
    avg_sim = _avg_similarity(retrieval_hits)
    scored: list[dict] = []
    for slot in slots or []:
        if not isinstance(slot, dict):
            continue
        satisfied = not violates_busy_times(slot, busy_times) and not conflicts_with_existing(
            slot, existing_tasks
        )
        enriched = dict(slot)
        enriched["score"] = slot_score(slot, avg_sim, satisfied)
        enriched["satisfied"] = satisfied
        scored.append(enriched)
    scored.sort(key=lambda s: s.get("score", 0.0), reverse=True)
    return scored


def confidence_score(
    retrieval_hits: list[dict],
    proposed_count: int,
    validated_count: int,
) -> float:
    """Combined retrieval + validation confidence in ``[0.0, 1.0]``.

    ``0.6 * avg(top-K similarity) + 0.4 * (validated / proposed)``. Returns
    0.0 if there are no retrieval hits. ``proposed_count`` of 0 yields a
    validation ratio of 0.
    """
    if not retrieval_hits:
        return 0.0
    avg_sim = _avg_similarity(retrieval_hits)
    if proposed_count <= 0:
        ratio = 0.0
    else:
        ratio = validated_count / proposed_count
    return _clip01(0.6 * avg_sim + 0.4 * ratio)


def confidence_label(score: float) -> str:
    """Bucket a numeric confidence into ``"high" | "medium" | "low"``."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "low"
    if s >= 0.7:
        return "high"
    if s >= 0.4:
        return "medium"
    return "low"


def _hits_from_recommendation(recommendation: Any) -> list[dict]:
    """Best-effort extraction of retrieval hits from a Recommendation.

    The ``Recommendation`` dataclass does not currently expose retrieval hits
    directly. We:

    1. Look for a ``retrieval_hits`` attribute (forward-compat with future RAG
       changes), and
    2. Otherwise synthesize a single pseudo-hit whose similarity equals
       ``recommendation.confidence`` — the RAG engine seeds ``confidence``
       with the average top-K similarity.

    This keeps :func:`apply_recommendation` working without a tight coupling
    to the RAG package.
    """
    direct = getattr(recommendation, "retrieval_hits", None)
    if isinstance(direct, list) and direct:
        return direct
    seed = getattr(recommendation, "confidence", None)
    try:
        seed_f = float(seed)
    except (TypeError, ValueError):
        return []
    return [{"similarity": seed_f}]


def apply_recommendation(
    recommendation: "Recommendation",
    busy_times: list,
    existing_tasks: list,
    auto_fix: bool = True,
) -> dict:
    """Run the full validate -> rank -> score pipeline.

    Steps:

    1. :func:`validate_slots` partitions the proposed slots into ``kept``
       (constraint-clean, possibly auto-shifted) and ``dropped``.
    2. :func:`rank_slots` orders the ``kept`` slots by score using the average
       retrieval similarity as the global retrieval signal.
    3. :func:`confidence_score` combines retrieval similarity with the
       validation pass-rate; :func:`confidence_label` buckets it.

    Returns a dict containing ``kept``, ``dropped``, ``ranked``,
    ``confidence``, ``confidence_label``, ``used_llm``, ``explanation`` and
    ``citations``.

    Note: ``Recommendation`` does not currently carry retrieval hits, so
    average similarity is derived from ``recommendation.confidence`` (the RAG
    engine seeds it with the top-K similarity average). See
    :func:`_hits_from_recommendation`.
    """
    proposed = list(getattr(recommendation, "proposed_tasks", []) or [])
    proposed_count = len(proposed)

    kept, dropped = validate_slots(
        proposed,
        busy_times or [],
        existing_tasks or [],
        auto_fix=auto_fix,
    )

    retrieval_hits = _hits_from_recommendation(recommendation)
    ranked = rank_slots(kept, retrieval_hits, busy_times or [], existing_tasks or [])

    final_confidence = confidence_score(
        retrieval_hits,
        proposed_count=proposed_count,
        validated_count=len(kept),
    )

    return {
        "kept": kept,
        "dropped": dropped,
        "ranked": ranked,
        "confidence": final_confidence,
        "confidence_label": confidence_label(final_confidence),
        "used_llm": getattr(recommendation, "used_llm", False),
        "explanation": getattr(recommendation, "explanation", ""),
        "citations": list(getattr(recommendation, "citations", []) or []),
    }
