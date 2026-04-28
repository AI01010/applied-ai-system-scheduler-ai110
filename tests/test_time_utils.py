"""Tests for time_utils — covers all accepted input formats + display modes."""

import pytest
from time_utils import parse_time, try_parse_time, format_time


# ── parse_time happy paths ───────────────────────────────────────────────────

@pytest.mark.parametrize("inp,expected", [
    # Canonical 24-hour
    ("08:00", "08:00"),
    ("8:00", "08:00"),
    ("23:59", "23:59"),
    ("00:00", "00:00"),

    # AM/PM with minutes
    ("8:30 AM", "08:30"),
    ("8:30am", "08:30"),
    ("8:30AM", "08:30"),
    ("12:30 AM", "00:30"),     # midnight half-hour
    ("12:30 PM", "12:30"),     # noon half-hour
    ("11:59 PM", "23:59"),
    ("1:00 PM", "13:00"),

    # AM/PM hour-only
    ("8 AM", "08:00"),
    ("8am", "08:00"),
    ("12 AM", "00:00"),         # midnight
    ("12 PM", "12:00"),         # noon
    ("1 PM", "13:00"),
    ("11 PM", "23:00"),

    # 4-digit military
    ("0830", "08:30"),
    ("2359", "23:59"),
    ("0000", "00:00"),

    # Hour-only 24h
    ("8", "08:00"),
    ("23", "23:00"),
    ("0", "00:00"),

    # Whitespace tolerance
    ("  08:00  ", "08:00"),
    ("  8 PM  ", "20:00"),
])
def test_parse_time_accepts(inp, expected):
    assert parse_time(inp) == expected


# ── parse_time rejects invalid input ─────────────────────────────────────────

@pytest.mark.parametrize("bad", [
    "",
    "   ",
    "abc",
    "25:00",        # hour out of range
    "12:60",        # minute out of range
    "13 PM",        # invalid 12-hour
    "0 AM",         # invalid 12-hour (no zero hour)
    "24:00",        # 24 isn't valid as a 24-hour hour
])
def test_parse_time_rejects(bad):
    with pytest.raises(ValueError):
        parse_time(bad)


def test_parse_time_none_raises():
    with pytest.raises(ValueError):
        parse_time(None)


# ── try_parse_time fallback behavior ─────────────────────────────────────────

def test_try_parse_time_returns_default_on_bad_input():
    assert try_parse_time("garbage", default="00:00") == "00:00"
    assert try_parse_time("", default=None) is None


def test_try_parse_time_returns_parsed_on_good_input():
    assert try_parse_time("8 PM") == "20:00"


# ── format_time ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("hhmm,fmt,expected", [
    ("08:00", "24h", "08:00"),
    ("08:00", "12h", "8:00 AM"),
    ("00:00", "12h", "12:00 AM"),
    ("12:00", "12h", "12:00 PM"),
    ("12:30", "12h", "12:30 PM"),
    ("13:00", "12h", "1:00 PM"),
    ("20:30", "12h", "8:30 PM"),
    ("23:59", "12h", "11:59 PM"),
])
def test_format_time(hhmm, fmt, expected):
    assert format_time(hhmm, fmt) == expected


def test_format_time_passthrough_on_malformed():
    # Should not crash; just return what was passed.
    assert format_time("not-a-time", "12h") == "not-a-time"
    assert format_time("", "12h") == ""


# ── Round-trip: parse -> format ──────────────────────────────────────────────

@pytest.mark.parametrize("user_input", ["8 AM", "8:30 PM", "0830", "23:00"])
def test_round_trip_parse_then_format_matches_canonical(user_input):
    parsed = parse_time(user_input)
    # 24h format should be the canonical string.
    assert format_time(parsed, "24h") == parsed
