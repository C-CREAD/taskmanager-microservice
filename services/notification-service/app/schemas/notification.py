import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.notification import NotificationChannel, NotificationType


# ── Inbound (from Task Service) ───────────────────────────────────────────────────

class InternalNotificationRequest(BaseModel):
    """Payload posted by Task Service or other internal services."""
    type: NotificationType
    recipient_id: str
    task_id: int | None = None
    task_title: str | None = None
    due_date: str | None = None
    assigned_by: str | None = None
    channel: NotificationChannel = NotificationChannel.ALL


# ── Outbound (to API consumers) ───────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: uuid.UUID
    recipient_id: str
    type: str
    channel: str
    title: str
    body: str
    is_read: bool
    is_sent: bool
    sent_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    count: int
    unread_count: int
    results: list[NotificationResponse]


# ── Device token registration ─────────────────────────────────────────────────────

class DeviceTokenRegisterRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=512)
    device_name: str | None = Field(None, max_length=100)


class DeviceTokenResponse(BaseModel):
    id: uuid.UUID
    user_id: str
    device_name: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Preferences ───────────────────────────────────────────────────────────────────

class NotificationPreferenceUpdate(BaseModel):
    email_enabled: bool | None = None
    push_enabled: bool | None = None
    websocket_enabled: bool | None = None
    muted_types: list[str] | None = None


class NotificationPreferenceResponse(BaseModel):
    user_id: str
    email_enabled: bool
    push_enabled: bool
    websocket_enabled: bool
    muted_types: list[str]
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_types(cls, pref):
        return cls(
            user_id=pref.user_id,
            email_enabled=pref.email_enabled,
            push_enabled=pref.push_enabled,
            websocket_enabled=pref.websocket_enabled,
            muted_types=[t for t in pref.muted_types.split(",") if t],
            updated_at=pref.updated_at,
        )
