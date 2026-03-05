from __future__ import annotations
import uuid
from datetime import date, datetime
from pydantic import BaseModel


class SummaryKPIs(BaseModel):
    total_tasks: int
    completed: int
    overdue: int
    due_today: int
    completed_today: int
    in_progress: int


class Rates(BaseModel):
    completion_rate: float
    on_time_rate: float
    completion_pct: float
    on_time_pct: float


class Productivity(BaseModel):
    score: float
    streak_days: int
    avg_tasks_per_day: float


class PriorityBreakdownItem(BaseModel):
    priority: str
    count: int
    percentage: float


class DailyTrendPoint(BaseModel):
    date: str
    completed: int
    created: int


class HeatmapPoint(BaseModel):
    date: str
    count: int
    weekday: int


class DashboardResponse(BaseModel):
    user_id: str
    generated_at: str
    summary: SummaryKPIs
    rates: Rates
    productivity: Productivity
    by_status: dict[str, int]
    by_priority: list[PriorityBreakdownItem]
    daily_trend: list[DailyTrendPoint]
    heatmap: list[HeatmapPoint]
    cached: bool = False


class TrendResponse(BaseModel):
    user_id: str
    period_days: int
    generated_at: str
    data: list[DailyTrendPoint]


class HeatmapResponse(BaseModel):
    user_id: str
    weeks: int
    generated_at: str
    data: list[HeatmapPoint]


class SnapshotResponse(BaseModel):
    id: uuid.UUID
    user_id: str
    snapshot_date: date
    tasks_created: int
    tasks_completed: int
    tasks_overdue: int
    completion_rate: float
    computed_at: datetime

    model_config = {"from_attributes": True}


class ProductivityScoreResponse(BaseModel):
    user_id: str
    score: float
    completion_rate: float
    on_time_rate: float
    avg_tasks_per_day: float
    streak_days: int
    computed_at: datetime

    model_config = {"from_attributes": True}
