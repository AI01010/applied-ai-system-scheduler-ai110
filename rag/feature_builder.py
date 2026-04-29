"""Turn an Owner+Pet pair into a natural-language search query for the retriever.

The query string is what gets embedded and matched against the knowledge-base
chunks, so it should be dense with the signals the KB documents are tagged on:
species, age, energy, health notes, and the owner's existing schedule shape.
"""

from __future__ import annotations

from datetime import date


def _coerce_busy_pairs(busy_entries) -> list:
    """Accept either ``[(start, end), ...]`` tuples OR ``[BusyBlock, ...]`` and
    return a flat list of ``(start, end)`` tuples. Keeps the formatter loose so
    legacy callers keep working alongside the new BusyBlock data model."""
    pairs = []
    for entry in busy_entries or []:
        if hasattr(entry, "start") and hasattr(entry, "end"):
            pairs.append((entry.start, entry.end))
        elif isinstance(entry, tuple) and len(entry) == 2:
            pairs.append((entry[0], entry[1]))
    return pairs


def _format_busy_times(busy_pairs) -> str:
    """Render ``[(start, end), ...]`` tuples as 'HH:MM-HH:MM, HH:MM-HH:MM'."""
    if not busy_pairs:
        return "no fixed busy times"
    return ", ".join(f"{start}-{end}" for start, end in busy_pairs)


def _format_existing_tasks(tasks) -> str:
    """Render a pet's task list as 'title at HH:MM, ...'."""
    if not tasks:
        return "none"
    parts = []
    for task in tasks:
        title = getattr(task, "title", "task")
        time_str = getattr(task, "time", "??:??")
        parts.append(f"{title} at {time_str}")
    return ", ".join(parts)


def build_query(owner, pet, target_date=None) -> str:
    """Turn an Owner+Pet into a natural-language search query.

    If the owner exposes ``active_busy_times(target_date)`` (the BusyBlock-aware
    Owner), the query reflects which busy windows actually fire on the target
    date. Otherwise it falls back to whatever ``owner.busy_times`` looks like —
    plain tuples or BusyBlocks — using ``_coerce_busy_pairs``.
    """
    name = getattr(pet, "name", "the pet")
    species = getattr(pet, "species", "pet")
    age = getattr(pet, "age", "?")
    energy = getattr(pet, "energy", "medium")
    health = (getattr(pet, "health_notes", "") or "").strip() or "none"
    tasks = getattr(pet, "tasks", []) or []

    target = target_date or date.today()
    if hasattr(owner, "active_busy_times"):
        busy_pairs = owner.active_busy_times(target)
    else:
        busy_pairs = _coerce_busy_pairs(getattr(owner, "busy_times", []))

    return (
        f"Daily care schedule for a {age}-year-old {energy}-energy {species} named {name}. "
        f"Owner busy {_format_busy_times(busy_pairs)}. "
        f"Existing tasks: {_format_existing_tasks(tasks)}. "
        f"Health notes: {health}."
    )
