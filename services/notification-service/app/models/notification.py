import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Enum, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.db.session import Base


class NotificationType(str, enum.Enum):
    TASK_CREATED   = "task_created"
    TASK_ASSIGNED  = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_DUE_SOON  = "task_due_soon"
    TASK_OVERDUE   = "task_overdue"
    SYSTEM         = "system"


class NotificationChannel(str, enum.Enum):
    EMAIL     = "email"
    PUSH      = "push"
    WEBSOCKET = "websocket"
    ALL       = "all"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recipient_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    type: Mapped[str] = mapped_column(
        Enum(NotificationType, name="notification_type_enum"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(
        Enum(NotificationChannel, name="notification_channel_enum"),
        nullable=False,
        default=NotificationChannel.ALL,
    )

    # Payload
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string for extra context

    # Delivery status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_notif_recipient_read", "recipient_id", "is_read"),
        Index("ix_notif_recipient_created", "recipient_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} type={self.type} to={self.recipient_id}>"


class DeviceToken(Base):
    """FCM push notification device tokens, one per user/device pair."""
    __tablename__ = "device_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    device_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<DeviceToken user={self.user_id} device={self.device_name}>"


class NotificationPreference(Base):
    """Per-user notification channel preferences."""
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)

    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    websocket_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Per-type overrides (stored as comma-separated muted types)
    muted_types: Mapped[str] = mapped_column(Text, default="")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def is_muted(self, notification_type: str) -> bool:
        return notification_type in self.muted_types.split(",")
