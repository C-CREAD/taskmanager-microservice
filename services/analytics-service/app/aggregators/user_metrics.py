"""
User productivity aggregator.
Combines live Task Service data with locally stored snapshots
to produce the full dashboard payload in a single call.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.aggregators.task_metrics import (
    build_daily_trend,
    build_heatmap,
    build_priority_breakdown,
    compute_completion_rate,
    compute_on_time_rate,
    compute_productivity_score,
    compute_streak,
)
from app.clients.http_client import TaskServiceClient

logger = logging.getLogger(__name__)


async def build_dashboard(user_id: str, auth_token: str) -> dict:
    """
    Aggregate all metrics needed for the productivity dashboard.
    Makes 2 calls to the Task Service:
      1. GET /tasks/stats/    — fast summary counts
      2. GET /tasks/?status=done (paginated) — for trend, heatmap, on-time rate
    """
    # --- Live stats from Task Service ---
    try:
        stats = await TaskServiceClient.get_user_stats(user_id, auth_token)
    except Exception as exc:
        logger.error("Failed to fetch stats from Task Service: %s", exc)
        stats = {
            "total": 0,
            "by_status": {},
            "by_priority": {},
            "overdue": 0,
            "due_today": 0,
            "completed_today": 0,
        }

    # --- Completed tasks for deeper analysis ---
    try:
        completed_tasks = await TaskServiceClient.get_all_completed_tasks(user_id, auth_token)
    except Exception as exc:
        logger.error("Failed to fetch completed tasks: %s", exc)
        completed_tasks = []

    # --- Derived metrics ---
    completion_rate   = compute_completion_rate(stats.get("by_status", {}))
    on_time_rate      = compute_on_time_rate(completed_tasks)
    streak            = compute_streak(completed_tasks)
    total_done        = stats.get("by_status", {}).get("done", 0)
    active_days       = max(len({
        t["completed_at"][:10] for t in completed_tasks if t.get("completed_at")
    }), 1)
    avg_per_day       = round(total_done / active_days, 2)

    productivity_score = compute_productivity_score(
        completion_rate, on_time_rate, avg_per_day, streak
    )

    daily_trend       = build_daily_trend(completed_tasks, days=30)
    heatmap           = build_heatmap(completed_tasks, weeks=12)
    priority_breakdown = build_priority_breakdown(stats.get("by_priority", {}))

    return {
        "user_id":            user_id,
        "generated_at":       datetime.now(timezone.utc).isoformat(),

        # Summary KPIs
        "summary": {
            "total_tasks":         stats.get("total", 0),
            "completed":           total_done,
            "overdue":             stats.get("overdue", 0),
            "due_today":           stats.get("due_today", 0),
            "completed_today":     stats.get("completed_today", 0),
            "in_progress":         stats.get("by_status", {}).get("in_progress", 0),
        },

        # Rates
        "rates": {
            "completion_rate":     completion_rate,        # 0.0–1.0
            "on_time_rate":        on_time_rate,           # 0.0–1.0
            "completion_pct":      round(completion_rate * 100, 1),
            "on_time_pct":         round(on_time_rate * 100, 1),
        },

        # Productivity
        "productivity": {
            "score":               productivity_score,     # 0–100
            "streak_days":         streak,
            "avg_tasks_per_day":   avg_per_day,
        },

        # Breakdowns
        "by_status":      stats.get("by_status", {}),
        "by_priority":    priority_breakdown,

        # Time-series (for charts)
        "daily_trend":    daily_trend,   # last 30 days
        "heatmap":        heatmap,       # last 12 weeks
    }
