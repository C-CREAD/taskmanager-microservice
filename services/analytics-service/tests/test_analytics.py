"""
Tests for the Analytics Service.
Task Service calls are mocked — no external dependencies needed.
Run with: pytest tests/ -v
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_analytics.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

FAKE_USER_ID = "aaaaaaaa-1111-2222-3333-000000000001"

# Patch auth dependency
from app.api.deps import CurrentUser, get_current_user

def mock_auth():
    return CurrentUser(
        id=FAKE_USER_ID,
        email="user@test.com",
        username="testuser",
        raw_token="fake.jwt.token",
    )

app.dependency_overrides[get_current_user] = mock_auth


async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# Mock Task Service responses
MOCK_STATS = {
    "total": 20,
    "by_status": {"todo": 5, "in_progress": 3, "in_review": 2, "done": 10, "cancelled": 0},
    "by_priority": {"low": 4, "medium": 8, "high": 5, "urgent": 3},
    "overdue": 2,
    "due_today": 1,
    "completed_today": 3,
}

MOCK_COMPLETED_TASKS = [
    {
        "id": i,
        "title": f"Task {i}",
        "status": "done",
        "priority": "medium",
        "created_at": f"2025-01-{i+1:02d}T10:00:00+00:00",
        "completed_at": f"2025-01-{i+1:02d}T14:00:00+00:00",
        "due_date": f"2025-01-{i+2:02d}T10:00:00+00:00",
    }
    for i in range(10)
]


# ── Metric computation unit tests ─────────────────────────────────────────────────

def test_compute_completion_rate():
    from app.aggregators.task_metrics import compute_completion_rate
    rate = compute_completion_rate({"todo": 5, "in_progress": 3, "done": 10, "in_review": 2})
    assert rate == pytest.approx(0.5, abs=0.01)


def test_compute_completion_rate_all_done():
    from app.aggregators.task_metrics import compute_completion_rate
    assert compute_completion_rate({"done": 5}) == 1.0


def test_compute_completion_rate_empty():
    from app.aggregators.task_metrics import compute_completion_rate
    assert compute_completion_rate({}) == 0.0


def test_compute_on_time_rate_all_on_time():
    from app.aggregators.task_metrics import compute_on_time_rate
    tasks = [
        {
            "due_date": "2025-06-10T10:00:00+00:00",
            "completed_at": "2025-06-09T10:00:00+00:00",
        }
    ]
    assert compute_on_time_rate(tasks) == 1.0


def test_compute_on_time_rate_late():
    from app.aggregators.task_metrics import compute_on_time_rate
    tasks = [
        {
            "due_date": "2025-06-01T10:00:00+00:00",
            "completed_at": "2025-06-10T10:00:00+00:00",
        }
    ]
    assert compute_on_time_rate(tasks) == 0.0


def test_build_daily_trend_length():
    from app.aggregators.task_metrics import build_daily_trend
    trend = build_daily_trend(MOCK_COMPLETED_TASKS, days=30)
    assert len(trend) == 30
    for point in trend:
        assert "date" in point
        assert "completed" in point
        assert "created" in point


def test_build_heatmap_length():
    from app.aggregators.task_metrics import build_heatmap
    heatmap = build_heatmap(MOCK_COMPLETED_TASKS, weeks=12)
    assert len(heatmap) == 12 * 7
    assert all("weekday" in h for h in heatmap)


def test_productivity_score_range():
    from app.aggregators.task_metrics import compute_productivity_score
    score = compute_productivity_score(
        completion_rate=0.8,
        on_time_rate=0.9,
        avg_tasks_per_day=3.5,
        streak_days=10,
    )
    assert 0 <= score <= 100


def test_productivity_score_perfect():
    from app.aggregators.task_metrics import compute_productivity_score
    score = compute_productivity_score(1.0, 1.0, 10.0, 30)
    assert score == 100.0


# ── API endpoint tests ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.aggregators.user_metrics.TaskServiceClient.get_user_stats", new_callable=AsyncMock)
@patch("app.aggregators.user_metrics.TaskServiceClient.get_all_completed_tasks", new_callable=AsyncMock)
@patch("app.core.cache.Cache.get", new_callable=AsyncMock, return_value=None)
@patch("app.core.cache.Cache.set", new_callable=AsyncMock)
async def test_dashboard_endpoint(mock_set, mock_get, mock_completed, mock_stats, client):
    mock_stats.return_value = MOCK_STATS
    mock_completed.return_value = MOCK_COMPLETED_TASKS

    resp = await client.get("/api/v1/analytics/dashboard", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "rates" in data
    assert "productivity" in data
    assert "daily_trend" in data
    assert "heatmap" in data
    assert data["summary"]["total_tasks"] == 20
    assert data["summary"]["completed"] == 10


@pytest.mark.asyncio
@patch("app.api.routes.TaskServiceClient.get_user_stats", new_callable=AsyncMock)
@patch("app.core.cache.Cache.get", new_callable=AsyncMock, return_value=None)
@patch("app.core.cache.Cache.set", new_callable=AsyncMock)
async def test_summary_endpoint(mock_set, mock_get, mock_stats, client):
    mock_stats.return_value = MOCK_STATS
    resp = await client.get("/api/v1/analytics/summary", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tasks"] == 20
    assert data["overdue"] == 2


@pytest.mark.asyncio
@patch("app.api.routes.TaskServiceClient.get_all_completed_tasks", new_callable=AsyncMock)
@patch("app.core.cache.Cache.get", new_callable=AsyncMock, return_value=None)
@patch("app.core.cache.Cache.set", new_callable=AsyncMock)
async def test_trend_endpoint(mock_set, mock_get, mock_completed, client):
    mock_completed.return_value = MOCK_COMPLETED_TASKS
    resp = await client.get("/api/v1/analytics/trend?days=14", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["period_days"] == 14
    assert len(data["data"]) == 14


@pytest.mark.asyncio
@patch("app.api.routes.TaskServiceClient.get_all_completed_tasks", new_callable=AsyncMock)
@patch("app.core.cache.Cache.get", new_callable=AsyncMock, return_value=None)
@patch("app.core.cache.Cache.set", new_callable=AsyncMock)
async def test_csv_export(mock_set, mock_get, mock_completed, client):
    mock_completed.return_value = MOCK_COMPLETED_TASKS
    resp = await client.get("/api/v1/analytics/export/csv?days=7", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/csv; charset=utf-8"
    assert "date,completed,created" in resp.text


@pytest.mark.asyncio
@patch("app.core.cache.Cache.delete_pattern", new_callable=AsyncMock)
async def test_cache_invalidation(mock_del, client):
    resp = await client.post("/api/v1/analytics/cache/invalidate", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 204
    mock_del.assert_called_once_with(f"analytics:{FAKE_USER_ID}:*")


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
