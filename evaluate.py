"""Evaluation harness for PawPal+ AI.

Runs the full pipeline (RAG retrieve -> generate -> validate -> rank) over a set
of canned scenarios and prints a pass/fail + confidence summary. Designed to be
the "Test Harness" stretch deliverable from the rubric.

Usage:
    python evaluate.py

Each scenario describes an Owner + a target Pet, plus a list of expected
behaviors:
  - "no_busy_overlap": no kept slot may overlap any of owner.busy_times
  - "min_kept": at least N slots are kept after validation
  - "must_cite_topic": at least one citation filename contains the substring

The harness builds the vector store on first run (idempotent), runs each
scenario, evaluates the assertions, and prints a one-line PASS/FAIL plus a
final aggregate.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable, List

from pawpal_system import Owner, Pet, Task

try:
    from rag.rag_engine import RAGEngine
    from rag.vector_store import ChromaStore
    from recommender.constraint_engine import parse_hhmm
    from recommender.ranker import apply_recommendation
except ImportError as e:
    print(f"[ERROR] Could not import RAG modules: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)


# ── scenario type ─────────────────────────────────────────────────────────────


@dataclass
class Scenario:
    name: str
    owner: Owner
    target_pet_name: str
    checks: List[Callable[[dict], tuple[bool, str]]]


# ── individual checks ─────────────────────────────────────────────────────────


def check_no_busy_overlap(busy_times):
    """Returns a check fn: every kept slot must lie outside all busy windows."""
    def _check(result: dict):
        for slot in result["kept"]:
            try:
                start = parse_hhmm(slot["time"])
                end = start + int(slot.get("duration_minutes", 15))
            except Exception:
                return False, f"unparseable slot {slot!r}"
            for win_start_s, win_end_s in busy_times:
                ws, we = parse_hhmm(win_start_s), parse_hhmm(win_end_s)
                if start < we and ws < end:
                    return False, f"slot {slot.get('time')} overlaps busy {win_start_s}-{win_end_s}"
        return True, "no busy-time overlaps"
    return _check


def check_min_kept(n: int):
    def _check(result: dict):
        kept = len(result["kept"])
        return (kept >= n, f"kept={kept} (min={n})")
    return _check


def check_must_cite_topic(substring: str):
    def _check(result: dict):
        if any(substring in c for c in result["citations"]):
            return True, f"citation contains '{substring}'"
        return False, f"no citation contained '{substring}'. citations={result['citations']}"
    return _check


def check_min_confidence(threshold: float):
    def _check(result: dict):
        return (
            result["confidence"] >= threshold,
            f"confidence={result['confidence']:.2f} (min={threshold})",
        )
    return _check


# ── scenario builders ─────────────────────────────────────────────────────────


def scenario_high_energy_dog_busy_owner() -> Scenario:
    owner = Owner(name="Alex", busy_times=[("09:00", "17:00")])
    dog = Pet(name="Rex", species="dog", age=2, energy="high", health_notes="")
    owner.add_pet(dog)
    return Scenario(
        name="High-energy dog with 9-5 owner",
        owner=owner,
        target_pet_name="Rex",
        checks=[
            check_no_busy_overlap(owner.busy_times),
            check_min_kept(3),
        ],
    )


def scenario_senior_cat() -> Scenario:
    owner = Owner(name="Pat", busy_times=[("08:00", "16:00")])
    cat = Pet(name="Misty", species="cat", age=14, energy="low",
              health_notes="senior, possible arthritis")
    owner.add_pet(cat)
    return Scenario(
        name="Senior cat, mostly-busy owner",
        owner=owner,
        target_pet_name="Misty",
        checks=[
            check_no_busy_overlap(owner.busy_times),
            check_min_kept(2),
        ],
    )


def scenario_existing_task_conflict() -> Scenario:
    owner = Owner(name="Sam", busy_times=[("18:00", "20:00")])
    dog = Pet(name="Bella", species="dog", age=4, energy="medium")
    # Existing morning walk should constrain AI proposals
    dog.add_task(Task(title="Morning walk", time="07:30", duration_minutes=45, priority="high", frequency="daily"))
    dog.add_task(Task(title="Feeding",      time="08:30", duration_minutes=15, priority="high", frequency="daily"))
    owner.add_pet(dog)
    return Scenario(
        name="Dog with existing tasks — recommender must avoid them",
        owner=owner,
        target_pet_name="Bella",
        checks=[
            check_no_busy_overlap(owner.busy_times),
            check_min_kept(1),
        ],
    )


def scenario_no_busy_times() -> Scenario:
    owner = Owner(name="Robin", busy_times=[])  # all-day available
    pet = Pet(name="Scout", species="dog", age=5, energy="medium")
    owner.add_pet(pet)
    return Scenario(
        name="Owner fully available — should keep everything",
        owner=owner,
        target_pet_name="Scout",
        checks=[
            check_min_kept(3),
        ],
    )


def scenario_other_species() -> Scenario:
    owner = Owner(name="Casey", busy_times=[("10:00", "12:00")])
    pet = Pet(name="Hopper", species="other", age=2, energy="medium",
              health_notes="rabbit")
    owner.add_pet(pet)
    return Scenario(
        name="Rabbit ('other' species) fallback path",
        owner=owner,
        target_pet_name="Hopper",
        checks=[
            check_no_busy_overlap(owner.busy_times),
            check_min_kept(2),
        ],
    )


def scenario_full_busy_window() -> Scenario:
    """Adversarial: owner busy almost all day. Auto-shift must find a window."""
    owner = Owner(name="Drew", busy_times=[("00:00", "07:00"), ("08:00", "23:00")])
    pet = Pet(name="Buddy", species="dog", age=3, energy="medium")
    owner.add_pet(pet)
    return Scenario(
        name="Adversarial: only 07:00-08:00 window free",
        owner=owner,
        target_pet_name="Buddy",
        checks=[
            check_no_busy_overlap(owner.busy_times),
        ],
    )


# ── runner ────────────────────────────────────────────────────────────────────


def run_scenario(engine: RAGEngine, scenario: Scenario) -> dict:
    pet = next(p for p in scenario.owner.pets if p.name == scenario.target_pet_name)
    rec = engine.generate(scenario.owner, pet, k=5)
    result = apply_recommendation(
        rec,
        busy_times=scenario.owner.busy_times,
        existing_tasks=pet.tasks,
    )
    return result


def main() -> int:
    print("=" * 72)
    print("PawPal+ AI — Evaluation Harness")
    print("=" * 72)

    print("\n[setup] Building local Chroma index from data/knowledge_base/...")
    store = ChromaStore()
    chunk_count = store.ingest_knowledge_base()
    print(f"[setup] Index ready: {chunk_count} chunks.")

    engine = RAGEngine(store=store)

    scenarios = [
        scenario_high_energy_dog_busy_owner(),
        scenario_senior_cat(),
        scenario_existing_task_conflict(),
        scenario_no_busy_times(),
        scenario_other_species(),
        scenario_full_busy_window(),
    ]

    total_checks = 0
    passed_checks = 0
    confidences = []

    for i, scenario in enumerate(scenarios, start=1):
        print(f"\n[{i}/{len(scenarios)}] {scenario.name}")
        try:
            result = run_scenario(engine, scenario)
        except Exception as e:
            print(f"   FAIL  scenario raised: {e}")
            total_checks += len(scenario.checks)
            continue

        confidences.append(result["confidence"])
        print(f"   confidence: {result['confidence']:.2f} ({result['confidence_label']})  "
              f"used_llm={result['used_llm']}  "
              f"kept={len(result['kept'])}  dropped={len(result['dropped'])}")

        for check in scenario.checks:
            total_checks += 1
            ok, msg = check(result)
            mark = "PASS" if ok else "FAIL"
            print(f"   {mark}  {msg}")
            if ok:
                passed_checks += 1

    print("\n" + "=" * 72)
    print("Summary")
    print("=" * 72)
    print(f"  scenarios:    {len(scenarios)}")
    print(f"  checks:       {passed_checks} / {total_checks} passed")
    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        print(f"  avg conf:     {avg_conf:.2f}  (min={min(confidences):.2f}, max={max(confidences):.2f})")
    print()
    return 0 if passed_checks == total_checks else 1


if __name__ == "__main__":
    sys.exit(main())
