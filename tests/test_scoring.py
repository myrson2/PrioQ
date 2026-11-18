"""Tests for the pure priority engine and its reference benchmarks."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.tasks.scoring import (
    SortMode,
    compute_priority,
    sort_tasks,
)

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
DAILY_STUDY_HOURS = 3.0


@dataclass(frozen=True)
class FakeTask:
    """Minimal stand-in for a scorable task."""

    id: int
    due_at: datetime
    grade_weight: float
    estimated_hours: float
    difficulty: int
    completed: bool = False
    completed_at: datetime | None = None


def task_a() -> FakeTask:
    """Quiz: due in 24h, 5%, 1h effort, difficulty 1."""
    return FakeTask(1, NOW + timedelta(hours=24), 5.0, 1.0, 1)


def task_b() -> FakeTask:
    """Project: due in 14 days, 30%, 20h effort, difficulty 4."""
    return FakeTask(2, NOW + timedelta(days=14), 30.0, 20.0, 4)


def task_c() -> FakeTask:
    """Overdue homework: due 2h ago, 10%, 2h effort, difficulty 3."""
    return FakeTask(3, NOW - timedelta(hours=2), 10.0, 2.0, 3)


def test_reference_task_a() -> None:
    """Quiz scores 20.2 and is urgent but not overdue."""
    result = compute_priority(task_a(), DAILY_STUDY_HOURS, NOW)
    assert result is not None
    assert result.score == pytest.approx(20.2, abs=0.05)
    assert result.time_pressure == pytest.approx(1 / 3)
    assert result.impact == pytest.approx(0.1)
    assert result.difficulty_factor == 0.0
    assert result.urgent is True
    assert result.overdue is False


def test_reference_task_b() -> None:
    """Project scores 56.1 with the documented factor breakdown."""
    result = compute_priority(task_b(), DAILY_STUDY_HOURS, NOW)
    assert result is not None
    assert result.score == pytest.approx(56.1, abs=0.05)
    assert result.time_pressure == pytest.approx(0.476, abs=0.001)
    assert result.impact == pytest.approx(0.6)
    assert result.difficulty_factor == pytest.approx(0.75)
    assert result.urgent is False
    assert result.overdue is False


def test_reference_task_c() -> None:
    """Overdue homework scores 64.5 with saturated time pressure."""
    result = compute_priority(task_c(), DAILY_STUDY_HOURS, NOW)
    assert result is not None
    assert result.score == pytest.approx(64.5)
    assert result.time_pressure == 1.0
    assert result.impact == pytest.approx(0.2)
    assert result.difficulty_factor == pytest.approx(0.5)
    assert result.urgent is True
    assert result.overdue is True


def test_urgent_cutoff_boundary() -> None:
    """Exactly 24h is urgent; 24h + 1s is not."""
    exactly = FakeTask(1, NOW + timedelta(hours=24), 5.0, 1.0, 1)
    later = FakeTask(2, NOW + timedelta(hours=24, seconds=1), 5.0, 1.0, 1)
    result_exact = compute_priority(exactly, DAILY_STUDY_HOURS, NOW)
    result_later = compute_priority(later, DAILY_STUDY_HOURS, NOW)
    assert result_exact is not None and result_later is not None
    assert result_exact.urgent is True
    assert result_later.urgent is False


def test_impact_is_capped_at_50_percent() -> None:
    """Weights at and above 50% cap impact at 1.0; zero weight gives 0.0."""
    capped = compute_priority(
        FakeTask(1, NOW + timedelta(days=10), 80.0, 1.0, 1), DAILY_STUDY_HOURS, NOW
    )
    zero = compute_priority(
        FakeTask(2, NOW + timedelta(days=10), 0.0, 1.0, 1), DAILY_STUDY_HOURS, NOW
    )
    assert capped is not None and zero is not None
    assert capped.impact == 1.0
    assert zero.impact == 0.0


def test_difficulty_factor_range() -> None:
    """Difficulty 1 maps to 0.0 and difficulty 5 maps to 1.0."""
    easy = compute_priority(
        FakeTask(1, NOW + timedelta(days=10), 10.0, 1.0, 1), DAILY_STUDY_HOURS, NOW
    )
    hard = compute_priority(
        FakeTask(2, NOW + timedelta(days=10), 10.0, 1.0, 5), DAILY_STUDY_HOURS, NOW
    )
    assert easy is not None and hard is not None
    assert easy.difficulty_factor == 0.0
    assert hard.difficulty_factor == 1.0


def test_bandwidth_sensitivity() -> None:
    """Less daily study time increases time pressure for future tasks."""
    task = task_b()
    relaxed = compute_priority(task, 3.0, NOW)
    busy = compute_priority(task, 1.0, NOW)
    assert relaxed is not None and busy is not None
    assert busy.time_pressure > relaxed.time_pressure


def test_completed_task_has_no_priority() -> None:
    """Completed tasks are not scored."""
    done = FakeTask(
        1, NOW + timedelta(days=1), 10.0, 1.0, 3, True, NOW - timedelta(hours=1)
    )
    assert compute_priority(done, DAILY_STUDY_HOURS, NOW) is None


def test_deadline_sort_order() -> None:
    """Incomplete tasks sort by due_at then id; completed tasks sink last."""
    old_done = FakeTask(
        9, NOW + timedelta(days=1), 10.0, 1.0, 3, True, NOW - timedelta(days=2)
    )
    new_done = FakeTask(
        8, NOW + timedelta(days=1), 10.0, 1.0, 3, True, NOW - timedelta(hours=1)
    )
    ordered = sort_tasks(
        [task_b(), old_done, task_a(), new_done, task_c()],
        SortMode.deadline,
        DAILY_STUDY_HOURS,
        NOW,
    )
    assert [task.id for task, _ in ordered] == [3, 1, 2, 8, 9]
    assert [priority for _, priority in ordered][-2:] == [None, None]


def test_smart_sort_order() -> None:
    """Incomplete tasks sort by score descending, then due_at, then id."""
    ordered = sort_tasks(
        [task_a(), task_b(), task_c()], SortMode.smart, DAILY_STUDY_HOURS, NOW
    )
    assert [task.id for task, _ in ordered] == [3, 2, 1]
    scores = [priority.score for _, priority in ordered if priority is not None]
    assert scores == sorted(scores, reverse=True)


def test_smart_sort_tie_break_by_due_at_then_id() -> None:
    """Equal smart scores tie-break on due_at ascending, then id ascending."""
    later = FakeTask(5, NOW + timedelta(hours=250), 10.0, 100.0, 1)
    earlier = FakeTask(4, NOW + timedelta(hours=240), 10.0, 100.0, 1)
    same_time_a = FakeTask(7, NOW + timedelta(hours=240), 10.0, 100.0, 1)
    ordered = sort_tasks(
        [later, same_time_a, earlier], SortMode.smart, DAILY_STUDY_HOURS, NOW
    )
    assert [task.id for task, _ in ordered] == [4, 7, 5]


def test_scoring_module_is_pure() -> None:
    """The scoring module must not import database or web framework code."""
    source = (Path(__file__).resolve().parents[1] / "app/tasks/scoring.py").read_text()
    assert "sqlalchemy" not in source.lower()
    assert "fastapi" not in source.lower()
