"""PawPal+ backend logic: Owner, Pet, Task, Scheduler."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


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
        # list of (start, end) HH:MM tuples — used by the AI recommender's constraint engine
        self.busy_times: list[tuple[str, str]] = busy_times or []
        self.pets: list[Pet] = []

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

    def detect_conflicts(self) -> list[str]:
        """Return warning strings for any two tasks at the same time, resolved by pet roster order."""
        # pet_order maps pet name -> its index in owner.pets (lower = higher priority)
        pet_order = {pet.name: i for i, pet in enumerate(self.owner.pets)}
        seen: dict[str, tuple] = {}   # time -> (task, pet_name)
        warnings = []
        for task, pet_name in self.get_tasks_with_pets():
            if task.time in seen:
                prev_task, prev_pet = seen[task.time]
                if pet_order[pet_name] < pet_order[prev_pet]:
                    winner, winner_pet = task, pet_name
                    loser,  loser_pet  = prev_task, prev_pet
                    seen[task.time] = (task, pet_name)
                else:
                    winner, winner_pet = prev_task, prev_pet
                    loser,  loser_pet  = task, pet_name
                warnings.append(
                    f"Conflict at {task.time}: '{winner.title}' ({winner_pet}) takes priority "
                    f"over '{loser.title}' ({loser_pet})"
                )
            else:
                seen[task.time] = (task, pet_name)
        return warnings

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
