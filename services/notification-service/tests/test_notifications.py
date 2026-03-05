"""
Tests for the Notification Service.
Run with: pytest tests/ -v

WebSocket and Celery calls are mocked.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_notifications.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db

# Mock JWT auth for all tests
FAKE_USER_ID = "aaaaaaaa-bbbb-cccc-dddd-000000000001"
FAKE_TOKEN = "fake.jwt.token"


def mock_get_current_user():
    from app.api.deps import CurrentUser
    return CurrentUser(id=FAKE_USER_ID, email="user@test.com", username="testuser")


from app.api.deps import get_current_user
app.dependency_overrides[get_current_user] = mock_get_current_user


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ── Internal notification dispatch ────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.api.routes.manager.publish", new_callable=AsyncMock)
@patch("app.api.routes.send_task_created_email.delay")
async def test_internal_notification_task_created(mock_email, mock_publish, client):
    resp = await client.post(
        "/api/notifications/internal",
        json={
            "type": "task_created",
            "recipient_id": FAKE_USER_ID,
            "task_id": 1,
            "task_title": "Write docs",
            "channel": "all",
        },
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "dispatched"
    mock_email.assert_called_once()
    mock_publish.assert_called_once()


@pytest.mark.asyncio
@patch("app.api.routes.manager.publish", new_callable=AsyncMock)
@patch("app.api.routes.send_task_assigned_email.delay")
async def test_internal_notification_task_assigned(mock_email, mock_publish, client):
    resp = await client.post(
        "/api/notifications/internal",
        json={
            "type": "task_assigned",
            "recipient_id": FAKE_USER_ID,
            "task_id": 2,
            "task_title": "Review PR",
        },
    )
    assert resp.status_code == 202


# ── List & read notifications ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_notifications_empty(client):
    resp = await client.get("/api/notifications/", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["unread_count"] == 0
    assert data["results"] == []


@pytest.mark.asyncio
@patch("app.api.routes.manager.publish", new_callable=AsyncMock)
@patch("app.api.routes.send_task_created_email.delay")
async def test_mark_notification_read(mock_email, mock_publish, client):
    # Create a notification first
    await client.post(
        "/api/notifications/internal",
        json={
            "type": "task_created",
            "recipient_id": FAKE_USER_ID,
            "task_id": 1,
            "task_title": "Test Task",
        },
    )

    # List to get the ID
    list_resp = await client.get(
        "/api/notifications/", headers={"Authorization": "Bearer x"}
    )
    notifs = list_resp.json()["results"]
    assert len(notifs) == 1
    notif_id = notifs[0]["id"]
    assert not notifs[0]["is_read"]

    # Mark as read
    read_resp = await client.patch(
        f"/api/notifications/{notif_id}/read",
        headers={"Authorization": "Bearer x"},
    )
    assert read_resp.status_code == 200
    assert read_resp.json()["is_read"]


@pytest.mark.asyncio
@patch("app.api.routes.manager.publish", new_callable=AsyncMock)
@patch("app.api.routes.send_task_created_email.delay")
async def test_unread_count(mock_email, mock_publish, client):
    # Create 2 notifications
    for i in range(2):
        await client.post(
            "/api/notifications/internal",
            json={
                "type": "task_created",
                "recipient_id": FAKE_USER_ID,
                "task_id": i,
                "task_title": f"Task {i}",
            },
        )

    resp = await client.get(
        "/api/notifications/unread-count", headers={"Authorization": "Bearer x"}
    )
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 2


@pytest.mark.asyncio
@patch("app.api.routes.manager.publish", new_callable=AsyncMock)
@patch("app.api.routes.send_task_created_email.delay")
async def test_mark_all_read(mock_email, mock_publish, client):
    for i in range(3):
        await client.post(
            "/api/notifications/internal",
            json={"type": "task_created", "recipient_id": FAKE_USER_ID, "task_id": i, "task_title": f"T{i}"},
        )

    resp = await client.post(
        "/api/notifications/read-all", headers={"Authorization": "Bearer x"}
    )
    assert resp.status_code == 204

    count_resp = await client.get(
        "/api/notifications/unread-count", headers={"Authorization": "Bearer x"}
    )
    assert count_resp.json()["unread_count"] == 0


# ── Device token ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_device_token(client):
    resp = await client.post(
        "/api/devices/",
        json={"token": "fcm_token_abc123xyz", "device_name": "My iPhone"},
        headers={"Authorization": "Bearer x"},
    )
    assert resp.status_code == 201
    assert resp.json()["device_name"] == "My iPhone"


# ── Preferences ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_default_preferences(client):
    resp = await client.get("/api/preferences/", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email_enabled"] is True
    assert data["push_enabled"] is True
    assert data["muted_types"] == []


@pytest.mark.asyncio
async def test_update_preferences(client):
    resp = await client.patch(
        "/api/preferences/",
        json={"email_enabled": False, "muted_types": ["task_created"]},
        headers={"Authorization": "Bearer x"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email_enabled"] is False
    assert "task_created" in data["muted_types"]


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
