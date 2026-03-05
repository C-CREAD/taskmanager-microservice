"""
Task metric aggregators.
These functions take raw data from the Task Service and compute
derived analytics used by the dashboard and trend endpoints.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone


def compute_completion_rate(by_status: dict) -> float:
    """
    Completion rate = done / (done + todo + in_progress + in_review)
    Excludes cancelled tasks from the denominator.
    """
    done = by_status.get("done", 0)
    active = (
        by_status.get("todo", 0)
        + by_status.get("in_progress", 0)
        + by_status.get("in_review", 0)
        + done
    )
    return round(done / active, 4) if active > 0 else 0.0


def compute_on_time_rate(completed_tasks: list[dict]) -> float:
    """
    On-time rate = tasks completed before or on due_date / tasks with a due_date that are done.
    """
    with_due = [t for t in completed_tasks if t.get("due_date") and t.get("completed_at")]
    if not with_due:
        return 0.0

    on_time = 0
    for task in with_due:
        due = datetime.fromisoformat(task["due_date"].replace("Z", "+00:00"))
        completed = datetime.fromisoformat(task["completed_at"].replace("Z", "+00:00"))
        if completed <= due:
            on_time += 1

    return round(on_time / len(with_due), 4)


def compute_streak(completed_tasks: list[dict]) -> int:
    """
    Count consecutive calendar days (up to today) on which the user
    completed at least one task.
    """
    if not completed_tasks:
        return 0

    completion_dates: set[date] = set()
    for t in completed_tasks:
        if t.get("completed_at"):
            dt = datetime.fromisoformat(t["completed_at"].replace("Z", "+00:00"))
            completion_dates.add(dt.date())

    streak = 0
    day = datetime.now(timezone.utc).date()
    while day in completion_dates:
        streak += 1
        day -= timedelta(days=1)

    return streak


def build_daily_trend(
    completed_tasks: list[dict],
    days: int = 30,
) -> list[dict]:
    """
    Return a list of {date, completed, created} dicts for the last N days.
    'created' count comes from created_at; 'completed' from completed_at.
    """
    today = datetime.now(timezone.utc).date()
    date_range = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]

    completed_by_day: dict[date, int] = defaultdict(int)
    created_by_day: dict[date, int] = defaultdict(int)

    for task in completed_tasks:
        if task.get("completed_at"):
            d = datetime.fromisoformat(task["completed_at"].replace("Z", "+00:00")).date()
            if d in set(date_range):
                completed_by_day[d] += 1
        if task.get("created_at"):
            d = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00")).date()
            if d in set(date_range):
                created_by_day[d] += 1

    return [
        {
            "date": str(d),
            "completed": completed_by_day[d],
            "created": created_by_day[d],
        }
        for d in date_range
    ]


def build_heatmap(completed_tasks: list[dict], weeks: int = 52) -> list[dict]:
    """
    GitHub-style activity heatmap.
    Returns {date, count, weekday} for the last N weeks.
    """
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(weeks=weeks)

    activity: dict[date, int] = defaultdict(int)
    for task in completed_tasks:
        if task.get("completed_at"):
            d = datetime.fromisoformat(task["completed_at"].replace("Z", "+00:00")).date()
            if d >= start:
                activity[d] += 1

    result = []
    day = start
    while day <= today:
        result.append({
            "date": str(day),
            "count": activity[day],
            "weekday": day.weekday(),  # 0=Monday
        })
        day += timedelta(days=1)

    return result


def build_priority_breakdown(by_priority: dict) -> list[dict]:
    total = sum(by_priority.values()) or 1
    return [
        {
            "priority": k,
            "count": v,
            "percentage": round(v / total * 100, 1),
        }
        for k, v in by_priority.items()
    ]


def compute_productivity_score(
    completion_rate: float,
    on_time_rate: float,
    avg_tasks_per_day: float,
    streak_days: int,
) -> float:
    """
    Weighted score 0–100:
      40% completion rate
      30% on-time rate
      20% avg tasks / day (capped at 10 tasks/day = full score)
      10% streak (capped at 30 days = full score)
    """
    activity_score = min(avg_tasks_per_day / 10, 1.0)
    streak_score   = min(streak_days / 30, 1.0)

    raw = (
        completion_rate * 0.40
        + on_time_rate  * 0.30
        + activity_score * 0.20
        + streak_score  * 0.10
    )
    return round(raw * 100, 1)
