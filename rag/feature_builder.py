"""Turn an Owner+Pet pair into a natural-language search query for the retriever.

The query string is what gets embedded and matched against the knowledge-base
chunks, so it should be dense with the signals the KB documents are tagged on:
species, age, energy, health notes, and the owner's existing schedule shape.
"""

from __future__ import annotations


def _format_busy_times(busy_times) -> str:
    """Render a list of (start, end) tuples as 'HH:MM-HH:MM, HH:MM-HH:MM'."""
    if not busy_times:
        return "no fixed busy times"
    return ", ".join(f"{start}-{end}" for start, end in busy_times)


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


def build_query(owner, pet) -> str:
    """Turn an Owner+Pet into a natural-language search query.

    Example output:
        "Daily care schedule for a 3-year-old high-energy dog named Mochi.
         Owner busy 09:00-17:00. Existing tasks: morning walk at 08:00,
         feeding at 18:00. Health notes: none."
    """
    name = getattr(pet, "name", "the pet")
    species = getattr(pet, "species", "pet")
    age = getattr(pet, "age", "?")
    energy = getattr(pet, "energy", "medium")
    health = (getattr(pet, "health_notes", "") or "").strip() or "none"
    tasks = getattr(pet, "tasks", []) or []
    busy = getattr(owner, "busy_times", []) or []

    return (
        f"Daily care schedule for a {age}-year-old {energy}-energy {species} named {name}. "
        f"Owner busy {_format_busy_times(busy)}. "
        f"Existing tasks: {_format_existing_tasks(tasks)}. "
        f"Health notes: {health}."
    )
