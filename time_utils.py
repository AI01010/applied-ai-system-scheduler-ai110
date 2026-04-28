"""Flexible time parsing + formatting helpers.

Canonical internal format is always 24-hour ``HH:MM`` (zero-padded), which is
what the rest of the system stores and sorts on. This module is the single
boundary that translates user-friendly inputs in (``parse_time``) and renders
display-friendly strings out (``format_time``).

Accepted input forms (all equivalent to ``08:30``):
    "08:30", "8:30", "0830", "8:30 AM", "8:30am", "8:30AM"
    "8 AM", "8am" (minutes default to 00)
    "8" (treated as 24-hour hour-only -> "08:00")

Edge cases:
    "12 AM" -> "00:00"   (midnight)
    "12 PM" -> "12:00"   (noon)
    "12:30 AM" -> "00:30"
"""

from __future__ import annotations

import re

# Patterns are tried in order; first match wins.
_PAT_HM_AMPM = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*(am|pm)\s*$", re.IGNORECASE)
_PAT_H_AMPM  = re.compile(r"^\s*(\d{1,2})\s*(am|pm)\s*$", re.IGNORECASE)
_PAT_HM_24   = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")
_PAT_HHMM_4D = re.compile(r"^\s*(\d{2})(\d{2})\s*$")
_PAT_H_24    = re.compile(r"^\s*(\d{1,2})\s*$")


def _to_24h(hour: int, minute: int, suffix: str) -> str:
    """Convert (hour, minute, 'am'|'pm') -> canonical 'HH:MM' 24-hour."""
    if not (1 <= hour <= 12) or not (0 <= minute <= 59):
        raise ValueError(f"invalid 12-hour time: {hour}:{minute}")
    if suffix == "am":
        h24 = 0 if hour == 12 else hour
    else:  # pm
        h24 = 12 if hour == 12 else hour + 12
    return f"{h24:02d}:{minute:02d}"


def parse_time(s: str) -> str:
    """Parse a flexible time string and return canonical ``HH:MM`` (24-hour).

    Raises ValueError if the string cannot be interpreted.
    """
    if s is None:
        raise ValueError("empty time")
    s = s.strip()
    if not s:
        raise ValueError("empty time")

    m = _PAT_HM_AMPM.match(s)
    if m:
        return _to_24h(int(m.group(1)), int(m.group(2)), m.group(3).lower())

    m = _PAT_H_AMPM.match(s)
    if m:
        return _to_24h(int(m.group(1)), 0, m.group(2).lower())

    m = _PAT_HM_24.match(s)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"
        raise ValueError(f"out of range: {s}")

    m = _PAT_HHMM_4D.match(s)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"
        raise ValueError(f"out of range: {s}")

    m = _PAT_H_24.match(s)
    if m:
        h = int(m.group(1))
        if 0 <= h <= 23:
            return f"{h:02d}:00"
        raise ValueError(f"out of range: {s}")

    raise ValueError(f"unparseable time: {s!r}")


def try_parse_time(s: str, default: str | None = None) -> str | None:
    """Like ``parse_time`` but returns ``default`` on failure instead of raising."""
    try:
        return parse_time(s)
    except (ValueError, TypeError):
        return default


def format_time(hhmm: str, fmt: str = "24h") -> str:
    """Format canonical ``HH:MM`` 24-hour string for display.

    fmt='24h' -> 'HH:MM' as-is.
    fmt='12h' -> 'h:MM AM' or 'h:MM PM' (no leading zero on the hour).

    If ``hhmm`` is malformed, returns it unchanged so callers don't crash.
    """
    if not hhmm or ":" not in hhmm:
        return hhmm or ""
    if fmt != "12h":
        return hhmm
    try:
        h_str, m_str = hhmm.split(":", 1)
        h = int(h_str)
        m = int(m_str)
        suffix = "AM" if h < 12 else "PM"
        h12 = h % 12
        if h12 == 0:
            h12 = 12
        return f"{h12}:{m:02d} {suffix}"
    except (ValueError, AttributeError):
        return hhmm
