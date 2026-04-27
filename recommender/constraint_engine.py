"""Constraint engine for the PawPal+ recommender.

Validates and (optionally) auto-shifts proposed task slots so they do not
collide with the owner's busy times or with already-scheduled tasks.

All times are normalized to integer minutes-since-midnight internally.
Slot intervals are treated as half-open ``[start, end)`` so a slot ending
exactly when a busy window begins is considered non-overlapping.
"""

from __future__ import annotations

from typing import Iterable, Optional

# Default duration (minutes) for slots that don't specify one.
_DEFAULT_DURATION = 15
# Total minutes in a day; used for wraparound during auto-shift.
_DAY_MINUTES = 24 * 60


def parse_hhmm(s: str) -> int:
    """Convert an ``"HH:MM"`` string to minutes since midnight.

    Raises ``ValueError`` if the string cannot be parsed.
    """
    if not isinstance(s, str):
        raise ValueError(f"Expected HH:MM string, got {type(s).__name__}")
    parts = s.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid HH:MM string: {s!r}")
    hours, minutes = int(parts[0]), int(parts[1])
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise ValueError(f"Out-of-range HH:MM string: {s!r}")
    return hours * 60 + minutes


def _format_hhmm(total_minutes: int) -> str:
    """Inverse of :func:`parse_hhmm` (wraps modulo 24h)."""
    total_minutes = total_minutes % _DAY_MINUTES
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def overlaps(slot_start: int, slot_end: int, win_start: int, win_end: int) -> bool:
    """Return True if ``[slot_start, slot_end)`` intersects ``[win_start, win_end)``.

    A slot ending exactly at ``win_start`` (or starting exactly at ``win_end``)
    does NOT overlap, since intervals are half-open.
    """
    return slot_start < win_end and win_start < slot_end


def slot_minutes(slot: dict) -> tuple[int, int]:
    """Return ``(start_min, end_min)`` for a slot dict.

    The slot must have a ``"time"`` key in ``"HH:MM"`` form. ``"duration_minutes"``
    is optional and defaults to :data:`_DEFAULT_DURATION` (15) when missing or
    non-positive.
    """
    start = parse_hhmm(slot["time"])
    duration = slot.get("duration_minutes", _DEFAULT_DURATION)
    try:
        duration = int(duration)
    except (TypeError, ValueError):
        duration = _DEFAULT_DURATION
    if duration <= 0:
        duration = _DEFAULT_DURATION
    return start, start + duration


def violates_busy_times(slot: dict, busy_times: Iterable[tuple[str, str]]) -> bool:
    """Return True if ``slot`` overlaps any ``(start, end)`` window in ``busy_times``."""
    try:
        slot_start, slot_end = slot_minutes(slot)
    except (KeyError, ValueError):
        # Malformed slot — treat as non-violating; ``validate_slots`` will drop it.
        return False
    for window in busy_times or []:
        try:
            win_start = parse_hhmm(window[0])
            win_end = parse_hhmm(window[1])
        except (KeyError, ValueError, IndexError, TypeError):
            continue
        if overlaps(slot_start, slot_end, win_start, win_end):
            return True
    return False


def conflicts_with_existing(slot: dict, existing_tasks: Iterable) -> bool:
    """Return True if ``slot`` overlaps any already-scheduled Task.

    ``existing_tasks`` is an iterable of objects exposing ``time`` (HH:MM
    string) and ``duration_minutes`` attributes — i.e. :class:`Task` instances
    from ``pawpal_system``.
    """
    try:
        slot_start, slot_end = slot_minutes(slot)
    except (KeyError, ValueError):
        return False
    for task in existing_tasks or []:
        time_str = getattr(task, "time", None)
        duration = getattr(task, "duration_minutes", _DEFAULT_DURATION)
        if time_str is None:
            continue
        try:
            task_start = parse_hhmm(time_str)
        except ValueError:
            continue
        try:
            duration = int(duration)
        except (TypeError, ValueError):
            duration = _DEFAULT_DURATION
        if duration <= 0:
            duration = _DEFAULT_DURATION
        task_end = task_start + duration
        if overlaps(slot_start, slot_end, task_start, task_end):
            return True
    return False


def auto_shift(
    slot: dict,
    busy_times: Iterable[tuple[str, str]],
    existing_tasks: Iterable,
    search_minutes: int = _DAY_MINUTES,
    step: int = 15,
) -> Optional[dict]:
    """Try shifting ``slot`` forward in ``step``-minute increments until it fits.

    Wraps past midnight if needed. Returns a NEW dict copy with an updated
    ``"time"`` field, or ``None`` if no fit is found within ``search_minutes``.
    The original slot dict is never mutated.
    """
    if "time" not in slot:
        return None
    try:
        original_start = parse_hhmm(slot["time"])
    except ValueError:
        return None
    duration = slot.get("duration_minutes", _DEFAULT_DURATION)
    try:
        duration = int(duration)
    except (TypeError, ValueError):
        duration = _DEFAULT_DURATION
    if duration <= 0:
        duration = _DEFAULT_DURATION

    if step <= 0:
        step = 15

    offset = step
    while offset <= search_minutes:
        candidate_start = (original_start + offset) % _DAY_MINUTES
        candidate = dict(slot)
        candidate["time"] = _format_hhmm(candidate_start)
        candidate["duration_minutes"] = duration
        if not violates_busy_times(candidate, busy_times) and not conflicts_with_existing(
            candidate, existing_tasks
        ):
            # Preserve original duration_minutes shape if caller didn't set it.
            if "duration_minutes" not in slot:
                candidate.pop("duration_minutes", None)
            return candidate
        offset += step
    return None


def validate_slots(
    slots: list[dict],
    busy_times: list[tuple[str, str]],
    existing_tasks: list,
    auto_fix: bool = True,
) -> tuple[list[dict], list[dict]]:
    """Partition ``slots`` into ``(kept, dropped)``.

    A slot is kept if it neither violates ``busy_times`` nor conflicts with
    ``existing_tasks``. When ``auto_fix`` is True, violating slots are first
    sent through :func:`auto_shift`; if a fit is found they are kept (with the
    new time) and tagged with ``"shifted": True``. Otherwise they go into the
    dropped list with a ``"drop_reason"`` tag.

    Malformed slots (missing ``"time"`` or unparseable) are always dropped
    with reason ``"malformed"``.
    """
    kept: list[dict] = []
    dropped: list[dict] = []

    for slot in slots or []:
        if not isinstance(slot, dict) or "time" not in slot:
            tagged = dict(slot) if isinstance(slot, dict) else {"raw": slot}
            tagged["drop_reason"] = "malformed"
            dropped.append(tagged)
            continue

        try:
            slot_minutes(slot)
        except (KeyError, ValueError):
            tagged = dict(slot)
            tagged["drop_reason"] = "malformed"
            dropped.append(tagged)
            continue

        busy_bad = violates_busy_times(slot, busy_times)
        existing_bad = conflicts_with_existing(slot, existing_tasks)

        if not busy_bad and not existing_bad:
            kept.append(dict(slot))
            continue

        if auto_fix:
            shifted = auto_shift(slot, busy_times, existing_tasks)
            if shifted is not None:
                shifted["shifted"] = True
                shifted["original_time"] = slot["time"]
                kept.append(shifted)
                continue

        tagged = dict(slot)
        if busy_bad and existing_bad:
            tagged["drop_reason"] = "busy_and_conflict"
        elif busy_bad:
            tagged["drop_reason"] = "busy_conflict"
        else:
            tagged["drop_reason"] = "task_conflict"
        dropped.append(tagged)

    return kept, dropped
