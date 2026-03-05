"""
Analytics Service API routes.

GET  /analytics/dashboard          — Full productivity dashboard (cached)
GET  /analytics/trend              — Daily trend for N days
GET  /analytics/heatmap            — Activity heatmap for N weeks
GET  /analytics/summary            — Lightweight KPI summary
GET  /analytics/snapshots          — Historical daily snapshots
GET  /analytics/score              — Productivity score
GET  /analytics/export/csv         — Export task metrics as CSV
POST /analytics/cache/invalidate   — Force-refresh cached dashboard
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select

from app.aggregators.task_metrics import build_daily_trend, build_heatmap
from app.aggregators.user_metrics import build_dashboard
from app.api.deps import AuthUser, DB
from app.clients.http_client import TaskServiceClient
from app.core.cache import cache
from app.models.report import DailySnapshot, UserProductivityScore
from app.schemas.analytics import (
    DashboardResponse,
    HeatmapResponse,
    ProductivityScoreResponse,
    SnapshotResponse,
    TrendResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _cache_key(user_id: str, suffix: str) -> str:
    return f"analytics:{user_id}:{suffix}"


# ── Dashboard ─────────────────────────────────────────────────────────────────────

@router.get(
    "/analytics/dashboard",
    response_model=DashboardResponse,
    summary="Full productivity dashboard — all metrics in one call",
)
async def get_dashboard(current_user: AuthUser):
    """
    Aggregates data from the Task Service and returns a complete dashboard payload.
    Result is cached in Redis for CACHE_TTL_SECONDS (default 5 minutes).
    """
    key = _cache_key(current_user.id, "dashboard")
    cached = await cache.get(key)
    if cached:
        cached["cached"] = True
        return cached

    data = await build_dashboard(current_user.id, current_user.raw_token)
    await cache.set(key, data)
    data["cached"] = False
    return data


# ── Summary KPIs ──────────────────────────────────────────────────────────────────

@router.get(
    "/analytics/summary",
    summary="Lightweight KPI summary — faster than /dashboard",
)
async def get_summary(current_user: AuthUser):
    """
    Calls only GET /tasks/stats/ (single Task Service request).
    Ideal for header badges / notification counts.
    """
    key = _cache_key(current_user.id, "summary")
    cached = await cache.get(key)
    if cached:
        return {**cached, "cached": True}

    try:
        stats = await TaskServiceClient.get_user_stats(current_user.id, current_user.raw_token)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Task Service unavailable: {exc}")

    result = {
        "user_id":        current_user.id,
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "total_tasks":    stats.get("total", 0),
        "completed":      stats.get("by_status", {}).get("done", 0),
        "overdue":        stats.get("overdue", 0),
        "due_today":      stats.get("due_today", 0),
        "completed_today": stats.get("completed_today", 0),
        "cached":         False,
    }
    await cache.set(key, result, ttl=120)  # shorter TTL for summary
    return result


# ── Trend ─────────────────────────────────────────────────────────────────────────

@router.get(
    "/analytics/trend",
    response_model=TrendResponse,
    summary="Daily task completion trend for the last N days",
)
async def get_trend(
    current_user: AuthUser,
    days: int = Query(30, ge=7, le=365, description="Number of days to look back"),
):
    key = _cache_key(current_user.id, f"trend:{days}")
    cached = await cache.get(key)
    if cached:
        return cached

    try:
        completed_tasks = await TaskServiceClient.get_all_completed_tasks(
            current_user.id, current_user.raw_token
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Task Service unavailable: {exc}")

    trend_data = build_daily_trend(completed_tasks, days=days)
    result = {
        "user_id":      current_user.id,
        "period_days":  days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data":         trend_data,
    }
    await cache.set(key, result)
    return result


# ── Heatmap ───────────────────────────────────────────────────────────────────────

@router.get(
    "/analytics/heatmap",
    response_model=HeatmapResponse,
    summary="Activity heatmap (GitHub-style) for the last N weeks",
)
async def get_heatmap(
    current_user: AuthUser,
    weeks: int = Query(12, ge=1, le=52, description="Number of weeks to look back"),
):
    key = _cache_key(current_user.id, f"heatmap:{weeks}")
    cached = await cache.get(key)
    if cached:
        return cached

    try:
        completed_tasks = await TaskServiceClient.get_all_completed_tasks(
            current_user.id, current_user.raw_token
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Task Service unavailable: {exc}")

    heatmap_data = build_heatmap(completed_tasks, weeks=weeks)
    result = {
        "user_id":      current_user.id,
        "weeks":        weeks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data":         heatmap_data,
    }
    await cache.set(key, result)
    return result


# ── Snapshots ─────────────────────────────────────────────────────────────────────

@router.get(
    "/analytics/snapshots",
    response_model=list[SnapshotResponse],
    summary="Historical daily snapshots stored in analytics DB",
)
async def get_snapshots(
    current_user: AuthUser,
    db: DB,
    limit: int = Query(30, ge=1, le=365),
):
    result = await db.execute(
        select(DailySnapshot)
        .where(DailySnapshot.user_id == current_user.id)
        .order_by(DailySnapshot.snapshot_date.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ── Productivity score ────────────────────────────────────────────────────────────

@router.get(
    "/analytics/score",
    response_model=ProductivityScoreResponse,
    summary="Productivity score (0–100) for the current user",
)
async def get_score(current_user: AuthUser, db: DB):
    """
    Returns the stored productivity score if available and recent (<24h).
    Falls back to live computation if not found.
    """
    result = await db.execute(
        select(UserProductivityScore).where(
            UserProductivityScore.user_id == current_user.id
        )
    )
    stored = result.scalar_one_or_none()

    if stored:
        age = (datetime.now(timezone.utc) - stored.computed_at).total_seconds()
        if age < 86400:  # less than 24 hours old
            return stored

    # Compute live
    dashboard = await build_dashboard(current_user.id, current_user.raw_token)
    prod = dashboard["productivity"]
    rates = dashboard["rates"]

    if stored:
        stored.score            = prod["score"]
        stored.completion_rate  = rates["completion_rate"]
        stored.on_time_rate     = rates["on_time_rate"]
        stored.avg_tasks_per_day = prod["avg_tasks_per_day"]
        stored.streak_days      = prod["streak_days"]
        stored.computed_at      = datetime.now(timezone.utc)
    else:
        stored = UserProductivityScore(
            user_id=current_user.id,
            score=prod["score"],
            completion_rate=rates["completion_rate"],
            on_time_rate=rates["on_time_rate"],
            avg_tasks_per_day=prod["avg_tasks_per_day"],
            streak_days=prod["streak_days"],
        )
        db.add(stored)

    await db.flush()
    await db.refresh(stored)
    return stored


# ── CSV export ────────────────────────────────────────────────────────────────────

@router.get(
    "/analytics/export/csv",
    summary="Export task completion metrics as a CSV file",
    response_class=Response,
)
async def export_csv(
    current_user: AuthUser,
    days: int = Query(30, ge=7, le=365),
):
    """
    Download a CSV with daily task metrics for the last N days.
    Useful for portfolio demos — shows actual file streaming.
    """
    try:
        completed_tasks = await TaskServiceClient.get_all_completed_tasks(
            current_user.id, current_user.raw_token
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Task Service unavailable: {exc}")

    trend = build_daily_trend(completed_tasks, days=days)

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["date", "completed", "created"])
    writer.writeheader()
    writer.writerows(trend)

    filename = f"taskforge_metrics_{current_user.id[:8]}_{days}d.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Cache invalidation ────────────────────────────────────────────────────────────

@router.post(
    "/analytics/cache/invalidate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Force-invalidate cached analytics for the current user",
)
async def invalidate_cache(current_user: AuthUser):
    """
    Call this after bulk task operations to get fresh data immediately.
    Deletes all analytics:user_id:* keys from Redis.
    """
    await cache.delete_pattern(f"analytics:{current_user.id}:*")
