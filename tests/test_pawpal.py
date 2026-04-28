"""Automated tests for PawPal+ core logic."""

from datetime import date, timedelta
import pytest
from pawpal_system import Task, Pet, Owner, Scheduler


# --- Helpers ---

def make_task(title="Walk", time="09:00", priority="medium", frequency="once"):
    return Task(title=title, time=time, duration_minutes=20, priority=priority, frequency=frequency)


def make_pet_with_tasks(*tasks):
    pet = Pet(name="Buddy", species="dog", age=2)
    for t in tasks:
        pet.add_task(t)
    return pet


# --- Phase 2 basic tests ---

def test_mark_complete_changes_status():
    """Marking a one-time task complete should set completed=True."""
    task = make_task(frequency="once")
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_count():
    """Adding a task to a pet should increase its task list length."""
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.get_tasks()) == 0
    pet.add_task(make_task())
    assert len(pet.get_tasks()) == 1


# --- Phase 5 extended tests ---

def test_sort_by_time_chronological():
    """sort_by_time should return tasks in HH:MM order regardless of insertion order."""
    owner = Owner("Jordan")
    pet = Pet(name="Mochi", species="dog", age=3)
    owner.add_pet(pet)
    pet.add_task(make_task("Evening", time="18:00"))
    pet.add_task(make_task("Morning", time="08:00"))
    pet.add_task(make_task("Noon",    time="12:00"))

    scheduler = Scheduler(owner)
    sorted_tasks = scheduler.sort_by_time()
    times = [t.time for t in sorted_tasks]
    assert times == sorted(times)


def test_recurring_daily_advances_due_date():
    """Marking a daily task complete should advance due_date by 1 day and reset completed."""
    task = make_task(frequency="daily")
    original_due = task.due_date
    task.mark_complete()
    assert task.completed is False
    assert task.due_date == original_due + timedelta(days=1)


def test_recurring_weekly_advances_due_date():
    """Marking a weekly task complete should advance due_date by 7 days."""
    task = make_task(frequency="weekly")
    original_due = task.due_date
    task.mark_complete()
    assert task.due_date == original_due + timedelta(weeks=1)


def test_conflict_detection_flags_same_time():
    """Scheduler should detect two tasks at the same time."""
    owner = Owner("Jordan")
    pet = Pet(name="Mochi", species="dog", age=3)
    owner.add_pet(pet)
    pet.add_task(make_task("Walk",    time="08:00"))
    pet.add_task(make_task("Feeding", time="08:00"))

    scheduler = Scheduler(owner)
    conflicts = scheduler.detect_conflicts()
    assert len(conflicts) == 1
    assert "08:00" in conflicts[0]


def test_no_conflict_different_times():
    """Scheduler should not flag tasks at different times."""
    owner = Owner("Jordan")
    pet = Pet(name="Mochi", species="dog", age=3)
    owner.add_pet(pet)
    pet.add_task(make_task("Walk",    time="08:00"))
    pet.add_task(make_task("Feeding", time="09:00"))

    scheduler = Scheduler(owner)
    assert scheduler.detect_conflicts() == []


def test_has_duplicate_detects_identical_task():
    """has_duplicate() flags tasks where all schedulable fields match."""
    pet = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(make_task("Walk", time="08:00", priority="high", frequency="daily"))

    same = make_task("Walk", time="08:00", priority="high", frequency="daily")
    assert pet.has_duplicate(same) is True


def test_has_duplicate_ignores_completion_state():
    """A duplicate is still a duplicate even if one task is marked done."""
    pet = Pet(name="Mochi", species="dog", age=3)
    done = make_task("Walk", time="08:00")
    done.completed = True
    pet.add_task(done)

    candidate = make_task("Walk", time="08:00")
    assert pet.has_duplicate(candidate) is True


def test_has_duplicate_distinguishes_on_any_field():
    """Different time, title, duration, priority, or frequency => not duplicate."""
    pet = Pet(name="Mochi", species="dog", age=3)
    pet.add_task(make_task("Walk", time="08:00", priority="high", frequency="daily"))

    # Different time
    assert pet.has_duplicate(make_task("Walk", time="09:00", priority="high", frequency="daily")) is False
    # Different title
    assert pet.has_duplicate(make_task("Run", time="08:00", priority="high", frequency="daily")) is False
    # Different priority
    assert pet.has_duplicate(make_task("Walk", time="08:00", priority="low", frequency="daily")) is False
    # Different frequency
    assert pet.has_duplicate(make_task("Walk", time="08:00", priority="high", frequency="weekly")) is False


def test_filter_by_status_returns_incomplete():
    """filter_by_status(False) should only return incomplete tasks."""
    owner = Owner("Jordan")
    pet = Pet(name="Mochi", species="dog", age=3)
    owner.add_pet(pet)
    done = make_task("Done task")
    done.completed = True
    pet.add_task(done)
    pet.add_task(make_task("Pending task"))

    scheduler = Scheduler(owner)
    pending = scheduler.filter_by_status(completed=False)
    assert all(not t.completed for t in pending)
    assert len(pending) == 1
