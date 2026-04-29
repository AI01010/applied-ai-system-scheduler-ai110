"""PawPal+ backend logic: Owner, Pet, Task, Scheduler, BusyBlock."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


# Day-of-week ordering used by BusyBlock.days (Python's date.weekday() convention).
_WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@dataclass
class BusyBlock:
    """A single busy window on the owner's calendar.

    The block is active on a given date when one of these is true:
      - ``on_date`` is set and equals the target date (one-time block), OR
      - ``days`` is empty (every day), OR
      - ``target_date.weekday()`` is in ``days``

    ``on_date`` always wins over ``days`` if both are set.
    """

    start: str                              # "HH:MM"
    end: str                                # "HH:MM"
    days: list = field(default_factory=list)   # 0=Mon..6=Sun, empty = every day
    on_date: Optional[date] = None             # one-time only

    def active_on(self, target: date) -> bool:
        """True if this block applies to the given calendar date."""
        if self.on_date is not None:
            return self.on_date == target
        if not self.days:
            return True
        return target.weekday() in self.days

    def label(self) -> str:
        """Short human-readable description of when this block fires."""
        if self.on_date is not None:
            return self.on_date.strftime("%a, %b %d, %Y")
        if not self.days:
            return "Every day"
        sorted_days = sorted(self.days)
        if sorted_days == [0, 1, 2, 3, 4]:
            return "Weekdays (Mon–Fri)"
        if sorted_days == [5, 6]:
            return "Weekends (Sat–Sun)"
        if sorted_days == [0, 1, 2, 3, 4, 5, 6]:
            return "Every day"
        if len(sorted_days) == 1:
            return f"Every {_WEEKDAY_NAMES[sorted_days[0]]}"
        return ", ".join(_WEEKDAY_NAMES[d] for d in sorted_days)


@dataclass
class Task:
    """Represents a single pet care activity."""

    title: str
    time: str                        # "HH:MM" format
    duration_minutes: int
    priority: str                    # "low" | "medium" | "high"
    description: str = ""
    frequency: str = "once"          # "once" | "daily" | "weekly"
    completed: bool = False
    due_date: date = field(default_factory=date.today)
    # Manual conflict-resolution boost. Higher beats lower at the same time
    # slot, and the boost beats the default pet-roster ordering. 0 means
    # "use the default rules."
    priority_override: int = 0

    def mark_complete(self):
        """Mark this task done and advance due_date for recurring tasks."""
        self.completed = True
        if self.frequency == "daily":
            self.due_date = self.due_date + timedelta(days=1)
            self.completed = False
        elif self.frequency == "weekly":
            self.due_date = self.due_date + timedelta(weeks=1)
            self.completed = False


@dataclass
class Pet:
    """Stores pet details and its associated task list."""

    name: str
    species: str
    age: int
    energy: str = "medium"           # "low" | "medium" | "high"
    health_notes: str = ""           # free-text, e.g. "senior, arthritis"
    tasks: list = field(default_factory=list)

    def add_task(self, task: Task):
        """Append a Task to this pet's task list."""
        self.tasks.append(task)

    def has_duplicate(self, task: Task) -> bool:
        """True if an identical task is already on this pet's calendar.

        Two tasks count as duplicates when title, time, duration, priority,
        and frequency all match — completion state and due_date are ignored.
        """
        return any(
            t.title == task.title
            and t.time == task.time
            and t.duration_minutes == task.duration_minutes
            and t.priority == task.priority
            and t.frequency == task.frequency
            for t in self.tasks
        )

    def remove_task(self, task: Task):
        """Remove a Task from this pet's task list."""
        self.tasks.remove(task)

    def get_tasks(self) -> list:
        """Return all tasks assigned to this pet."""
        return self.tasks


class Owner:
    """Manages a collection of pets and provides a unified task view."""

    def __init__(self, name: str, contact_info: str = "", busy_times: Optional[list] = None):
        self.name = name
        self.contact_info = contact_info
        # Calendar blocks. Each entry is a BusyBlock with start/end times plus
        # day-of-week or specific-date scoping. Legacy tuple inputs are
        # auto-promoted to "every day" BusyBlocks for backward compat.
        self.busy_times: list[BusyBlock] = []
        if busy_times:
            for entry in busy_times:
                if isinstance(entry, BusyBlock):
                    self.busy_times.append(entry)
                elif isinstance(entry, tuple) and len(entry) == 2:
                    self.busy_times.append(BusyBlock(start=entry[0], end=entry[1]))
        self.pets: list[Pet] = []

    def active_busy_times(self, target_date: Optional[date] = None) -> list:
        """Return ``[(start, end), ...]`` tuples of blocks active on ``target_date``.

        Defaults to today. This is the shape the recommender's constraint
        engine consumes — keeps that layer agnostic to recurrence.
        """
        target = target_date or date.today()
        return [(b.start, b.end) for b in self.busy_times if b.active_on(target)]

    def add_pet(self, pet: Pet):
        """Add a Pet to the owner's roster."""
        self.pets.append(pet)

    def remove_pet(self, pet: Pet):
        """Remove a Pet (and all its tasks) from the owner's roster."""
        self.pets.remove(pet)

    def get_all_tasks(self) -> list[Task]:
        """Return a flat list of every task across all pets."""
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.get_tasks())
        return all_tasks


class Scheduler:
    """Retrieves, organizes, and manages tasks across all of an owner's pets."""

    def __init__(self, owner: Owner):
        self.owner = owner

    def get_all_tasks(self) -> list[Task]:
        """Return all tasks from the owner's pets."""
        return self.owner.get_all_tasks()

    def sort_by_time(self) -> list[Task]:
        """Return all tasks sorted chronologically by time (HH:MM)."""
        return sorted(self.get_all_tasks(), key=lambda t: t.time)

    def filter_by_status(self, completed: bool) -> list[Task]:
        """Return tasks matching the given completion status."""
        return [t for t in self.get_all_tasks() if t.completed == completed]

    def filter_by_pet(self, pet_name: str) -> list[Task]:
        """Return tasks belonging to the named pet."""
        for pet in self.owner.pets:
            if pet.name.lower() == pet_name.lower():
                return pet.get_tasks()
        return []

    def conflict_pairs(self) -> list[dict]:
        """Return structured conflict info for each same-time clash.

        Each entry: ``{"time", "winner_task", "winner_pet", "loser_task",
        "loser_pet", "reason"}``. ``reason`` is "manual override" when a
        Task.priority_override settled the order, or "pet roster" when the
        default ordering applied.
        """
        # pet_order: lower index = higher default priority
        pet_order = {pet.name: i for i, pet in enumerate(self.owner.pets)}
        seen: dict[str, tuple] = {}  # time -> (task, pet_name)
        pairs: list[dict] = []

        for task, pet_name in self.get_tasks_with_pets():
            if task.time not in seen:
                seen[task.time] = (task, pet_name)
                continue

            prev_task, prev_pet = seen[task.time]

            # Override beats roster. Higher override wins; ties fall through.
            if task.priority_override != prev_task.priority_override:
                if task.priority_override > prev_task.priority_override:
                    winner_task, winner_pet, loser_task, loser_pet = task, pet_name, prev_task, prev_pet
                else:
                    winner_task, winner_pet, loser_task, loser_pet = prev_task, prev_pet, task, pet_name
                reason = "manual override"
            else:
                # Default: pet roster order
                if pet_order[pet_name] < pet_order[prev_pet]:
                    winner_task, winner_pet, loser_task, loser_pet = task, pet_name, prev_task, prev_pet
                else:
                    winner_task, winner_pet, loser_task, loser_pet = prev_task, prev_pet, task, pet_name
                reason = "pet roster"

            seen[task.time] = (winner_task, winner_pet)
            pairs.append({
                "time":        task.time,
                "winner_task": winner_task,
                "winner_pet":  winner_pet,
                "loser_task":  loser_task,
                "loser_pet":   loser_pet,
                "reason":      reason,
            })
        return pairs

    def detect_conflicts(self) -> list[str]:
        """Return human-readable warning strings for each detected conflict.

        Wraps :meth:`conflict_pairs` to preserve the original API.
        """
        return [
            f"Conflict at {p['time']}: '{p['winner_task'].title}' ({p['winner_pet']}) "
            f"takes priority over '{p['loser_task'].title}' ({p['loser_pet']})"
            for p in self.conflict_pairs()
        ]

    def override_winner(self, time: str, winner_task: Task) -> None:
        """Make ``winner_task`` win every conflict at ``time``.

        Sets ``winner_task.priority_override`` to one above the current max
        among same-time tasks, and resets all other same-time tasks to 0.
        """
        same_time = [t for t, _ in self.get_tasks_with_pets() if t.time == time]
        if winner_task not in same_time:
            return
        new_boost = max((t.priority_override for t in same_time), default=0) + 1
        for t in same_time:
            t.priority_override = 0
        winner_task.priority_override = new_boost

    def get_tasks_with_pets(self) -> list[tuple]:
        """Return a list of (task, pet_name) sorted by task time."""
        pairs = []
        for pet in self.owner.pets:
            for task in pet.get_tasks():
                pairs.append((task, pet.name))
        return sorted(pairs, key=lambda p: p[0].time)

    def delete_task(self, task: Task):
        """Remove a task from whichever pet owns it."""
        for pet in self.owner.pets:
            if task in pet.tasks:
                pet.remove_task(task)
                return

    def completion_progress(self) -> tuple[int, int]:
        """Return (completed_count, total_count) across all tasks."""
        all_tasks = self.get_all_tasks()
        done = sum(1 for t in all_tasks if t.completed)
        return done, len(all_tasks)

    def generate_schedule(self) -> list[Task]:
        """Return today's incomplete tasks sorted by time, with conflicts noted."""
        return self.filter_by_status(completed=False)
