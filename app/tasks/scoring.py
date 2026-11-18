"""Pure priority engine: explainable scores and queue ordering."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Protocol, TypeVar

WEIGHT_TIME_PRESSURE = 0.50
WEIGHT_IMPACT = 0.35
WEIGHT_DIFFICULTY = 0.15
IMPACT_CAP_PERCENT = 50.0
URGENT_WINDOW_HOURS = 24.0

T = TypeVar("T")


class SortMode(StrEnum):
    deadline = "deadline"
    smart = "smart"


@dataclass(frozen=True)
class PriorityResult:
    score: float
    time_pressure: float
    impact: float
    difficulty_factor: float
    hours_until_due: float
    urgent: bool
    overdue: bool


class ScorableTask(Protocol):
    id: int
    due_at: datetime
    grade_weight: float
    estimated_hours: float
    difficulty: int
    completed: bool
    completed_at: datetime | None


def compute_priority(
    task: ScorableTask, daily_study_hours: float, now: datetime
) -> PriorityResult | None:
    """Return the explainable priority breakdown for an incomplete task."""
    if task.completed:
        return None

    hours_until_due = (task.due_at - now).total_seconds() / 3600.0 # in seconds

    if hours_until_due <= 0:
        time_pressure = 1.0 # ?
    else:
        available_study_hours = (hours_until_due / 24.0) * daily_study_hours 
        time_pressure = min(task.estimated_hours / available_study_hours, 1.0) # the closer to 1.0 the urgent it is

    impact = min(task.grade_weight / IMPACT_CAP_PERCENT, 1.0)
    difficulty_factor = (task.difficulty - 1) / 4.0
    score = 100.0 * (
        WEIGHT_TIME_PRESSURE * time_pressure
        + WEIGHT_IMPACT * impact
        + WEIGHT_DIFFICULTY * difficulty_factor
    )

    return PriorityResult(
        score=score,
        time_pressure=time_pressure,
        impact=impact,
        difficulty_factor=difficulty_factor,
        hours_until_due=hours_until_due,
        urgent=hours_until_due <= URGENT_WINDOW_HOURS,
        overdue=hours_until_due < 0,
    )


def sort_tasks[T](
    tasks: Iterable[T],
    mode: SortMode,
    daily_study_hours: float,
    now: datetime,
) -> list[tuple[T, PriorityResult | None]]:
    """Sort tasks by the requested mode, sinking completed tasks to the bottom."""
    
    incomplete: list[T] = [] # list of incomplete tasks
    completed: list[T] = [] # list of complete tasks

    for task in tasks:
        if getattr(task, "completed", False):
            completed.append(task) # add if completed to completed_list
        else:
            incomplete.append(task) # add if incomplete to incomplete_list

    # ====================================================================================

    scored: list[tuple[T, PriorityResult]] = [] # then make a list to score the incomplete tasks
    
    for task in incomplete:
        result = compute_priority(task, daily_study_hours, now) # score using compute_priority()
        if result is not None: # defensive coding only
            scored.append((task, result))
    
    # ====================================================================================
    
    if mode == SortMode.smart:
        scored.sort(
            key=lambda pair: (-pair[1].score, pair[0].due_at, pair[0].id)
        )
    elif mode == SortMode.deadline:
        scored.sort(key=lambda pair: (pair[0].due_at, pair[0].id))
    else:
        raise ValueError(f"Unsupported sort mode: {mode}")  

    # Stable sort by id first, then by completed_at descending, preserving id order on ties.
    completed.sort(key=lambda task: task.id)
    completed.sort(
        key=lambda task: task.completed_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    return [[(task, result) for task, result in scored] + [(task, None) for task in completed]]
