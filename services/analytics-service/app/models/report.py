"""
The Analytics Service stores pre-aggregated daily snapshots to power
fast dashboard queries without hitting the Task Service on every request.

Snapshots are computed by a nightly Celery Beat task and stored here.
Real-time stats are fetched live from the Task Service and cached in Redis.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DailySnapshot(Base):
    """
    One row per (user_id, snapshot_date).
    Stores aggregated task metrics for that calendar day.
    """
    __tablename__ = "daily_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Task counts
    tasks_created: Mapped[int] = mapped_column(Integer, default=0)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_overdue: Mapped[int] = mapped_column(Integer, default=0)
    tasks_in_progress: Mapped[int] = mapped_column(Integer, default=0)

    # Completion rate 0.0–1.0
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # Priority breakdown (JSON stored as text for SQLite compat)
    priority_breakdown: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Category breakdown (JSON)
    category_breakdown: Mapped[str | None] = mapped_column(Text, nullable=True)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DailySnapshot user={self.user_id} date={self.snapshot_date}>"


class UserProductivityScore(Base):
    """
    Rolling productivity score per user, updated weekly.
    Score is 0–100 based on completion rate, on-time rate, and activity.
    """
    __tablename__ = "user_productivity_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)

    score: Mapped[float] = mapped_column(Float, default=0.0)          # 0–100
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0) # 0–1
    on_time_rate: Mapped[float] = mapped_column(Float, default=0.0)    # 0–1
    avg_tasks_per_day: Mapped[float] = mapped_column(Float, default=0.0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)       # consecutive active days

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ProductivityScore user={self.user_id} score={self.score:.1f}>"
