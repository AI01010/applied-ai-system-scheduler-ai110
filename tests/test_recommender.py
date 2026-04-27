"""Tests for the recommender layer (constraint engine + ranker).

These tests are pure-Python and need no external services — they exercise the
constraint validation and confidence math directly.
"""

from types import SimpleNamespace

import pytest

from recommender.constraint_engine import (
    auto_shift,
    conflicts_with_existing,
    overlaps,
    parse_hhmm,
    slot_minutes,
    validate_slots,
    violates_busy_times,
)
from recommender.ranker import (
    apply_recommendation,
    confidence_label,
    confidence_score,
    rank_slots,
    slot_score,
)


# ── parse / overlap primitives ────────────────────────────────────────────────


def test_parse_hhmm_basic():
    assert parse_hhmm("00:00") == 0
    assert parse_hhmm("09:30") == 9 * 60 + 30
    assert parse_hhmm("23:59") == 23 * 60 + 59


def test_parse_hhmm_rejects_garbage():
    with pytest.raises(ValueError):
        parse_hhmm("99:99")
    with pytest.raises(ValueError):
        parse_hhmm("noon")


def test_overlaps_half_open():
    # [60, 120) intersects [90, 150) — overlap
    assert overlaps(60, 120, 90, 150) is True
    # [60, 120) does NOT intersect [120, 180) — adjacent, half-open
    assert overlaps(60, 120, 120, 180) is False
    # disjoint
    assert overlaps(60, 80, 100, 120) is False


def test_slot_minutes_default_duration():
    s, e = slot_minutes({"time": "08:00"})
    assert s == 8 * 60
    assert e == 8 * 60 + 15  # default duration is 15 when missing


# ── busy-time + existing-task validation ──────────────────────────────────────


def test_violates_busy_times_true():
    slot = {"time": "10:00", "duration_minutes": 30}
    busy = [("09:00", "11:00")]
    assert violates_busy_times(slot, busy) is True


def test_violates_busy_times_false_when_outside():
    slot = {"time": "08:00", "duration_minutes": 30}
    busy = [("09:00", "11:00")]
    assert violates_busy_times(slot, busy) is False


def test_violates_busy_times_adjacent_is_ok():
    # Slot ends at 09:00 exactly when busy begins — half-open intervals → no overlap
    slot = {"time": "08:30", "duration_minutes": 30}
    busy = [("09:00", "11:00")]
    assert violates_busy_times(slot, busy) is False


def test_conflicts_with_existing_task():
    # Mock Task object via SimpleNamespace
    existing = [SimpleNamespace(time="08:00", duration_minutes=30)]
    slot = {"time": "08:15", "duration_minutes": 10}
    assert conflicts_with_existing(slot, existing) is True


def test_no_conflict_with_distant_task():
    existing = [SimpleNamespace(time="08:00", duration_minutes=30)]
    slot = {"time": "12:00", "duration_minutes": 10}
    assert conflicts_with_existing(slot, existing) is False


# ── auto_shift ────────────────────────────────────────────────────────────────


def test_auto_shift_finds_next_valid_slot():
    slot = {"title": "Walk", "time": "10:00", "duration_minutes": 30}
    busy = [("09:00", "11:00")]
    shifted = auto_shift(slot, busy, [])
    assert shifted is not None
    # Should advance to at least 11:00 (when busy ends, half-open)
    assert parse_hhmm(shifted["time"]) >= 11 * 60


def test_auto_shift_returns_none_when_impossible():
    # Busy all day + step bigger than search makes a fit impossible.
    slot = {"title": "Walk", "time": "10:00", "duration_minutes": 30}
    busy = [("00:00", "23:59")]
    shifted = auto_shift(slot, busy, [], search_minutes=60, step=15)
    # Even within an hour of search, no valid 30-min slot exists
    assert shifted is None


# ── validate_slots (the main entry point) ─────────────────────────────────────


def test_validate_slots_keeps_clean_slots():
    slots = [
        {"title": "Morning walk", "time": "07:00", "duration_minutes": 30},
        {"title": "Evening walk", "time": "18:00", "duration_minutes": 30},
    ]
    busy = [("09:00", "17:00")]
    kept, dropped = validate_slots(slots, busy, [])
    assert len(kept) == 2
    assert len(dropped) == 0


def test_validate_slots_auto_shifts_violators():
    slots = [{"title": "Walk", "time": "10:00", "duration_minutes": 30}]
    busy = [("09:00", "17:00")]
    kept, dropped = validate_slots(slots, busy, [], auto_fix=True)
    assert len(kept) == 1
    assert kept[0].get("shifted") is True
    assert kept[0].get("original_time") == "10:00"
    # New time must be outside the busy window
    assert parse_hhmm(kept[0]["time"]) >= 17 * 60


def test_validate_slots_drops_when_auto_fix_disabled():
    slots = [{"title": "Walk", "time": "10:00", "duration_minutes": 30}]
    busy = [("09:00", "17:00")]
    kept, dropped = validate_slots(slots, busy, [], auto_fix=False)
    assert len(kept) == 0
    assert len(dropped) == 1
    assert dropped[0]["drop_reason"] == "busy_conflict"


def test_validate_slots_handles_malformed():
    slots = [{"title": "no time field"}, {"time": "08:00"}]
    kept, dropped = validate_slots(slots, [], [])
    assert len(kept) == 1
    assert len(dropped) == 1
    assert dropped[0]["drop_reason"] == "malformed"


# ── ranker: scoring + confidence ──────────────────────────────────────────────


def test_slot_score_components():
    # avg_sim=0.5, satisfied=True → 0.6*0.5 + 0.4*1.0 = 0.7
    assert slot_score({}, 0.5, True) == pytest.approx(0.7)
    # satisfied=False → 0.6*0.5 + 0.4*0 = 0.3
    assert slot_score({}, 0.5, False) == pytest.approx(0.3)


def test_rank_slots_orders_satisfied_first():
    slots = [
        {"title": "bad", "time": "10:00", "duration_minutes": 15},   # in busy window
        {"title": "good", "time": "08:00", "duration_minutes": 15},  # outside
    ]
    busy = [("09:00", "17:00")]
    hits = [{"score": 0.8}, {"score": 0.6}]   # avg = 0.7
    ranked = rank_slots(slots, hits, busy, [])
    # "good" (satisfied) should rank higher than "bad" (unsatisfied)
    assert ranked[0]["title"] == "good"
    assert ranked[0]["satisfied"] is True
    assert ranked[1]["satisfied"] is False
    assert ranked[0]["score"] > ranked[1]["score"]


def test_confidence_score_formula():
    hits = [{"score": 0.8}, {"score": 0.6}]   # avg = 0.7
    # 0.6*0.7 + 0.4*(2/2) = 0.42 + 0.4 = 0.82
    assert confidence_score(hits, proposed_count=2, validated_count=2) == pytest.approx(0.82)


def test_confidence_score_zero_without_hits():
    assert confidence_score([], 5, 5) == 0.0


def test_confidence_label_buckets():
    assert confidence_label(0.85) == "high"
    assert confidence_label(0.5)  == "medium"
    assert confidence_label(0.2)  == "low"
    assert confidence_label(0.7)  == "high"   # boundary inclusive
    assert confidence_label(0.4)  == "medium" # boundary inclusive


# ── full pipeline: apply_recommendation ───────────────────────────────────────


def test_apply_recommendation_end_to_end():
    """Build a fake Recommendation and run it through validate -> rank -> score."""

    class FakeRec:
        def __init__(self):
            self.proposed_tasks = [
                {"title": "Morning walk", "time": "07:00", "duration_minutes": 30,
                 "priority": "high", "rationale": "energy"},
                {"title": "Bad slot",     "time": "10:00", "duration_minutes": 30,
                 "priority": "medium", "rationale": "in busy window"},
            ]
            self.explanation = "Sample plan"
            self.citations = ["dog_high_energy_schedule.md"]
            self.confidence = 0.7
            self.used_llm = False

    busy = [("09:00", "17:00")]
    result = apply_recommendation(FakeRec(), busy_times=busy, existing_tasks=[])

    assert "kept" in result and "dropped" in result and "ranked" in result
    assert result["confidence_label"] in {"high", "medium", "low"}
    assert result["used_llm"] is False
    # Both should be kept thanks to auto-shift on the bad slot
    assert len(result["kept"]) == 2
    # The auto-shifted one should carry the "shifted" tag
    assert any(s.get("shifted") for s in result["kept"])
