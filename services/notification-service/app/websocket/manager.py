"""
WebSocket Connection Manager with Redis Pub/Sub fan-out.

Architecture:
  - Each connected client subscribes to a personal Redis channel: ws:user:{user_id}
  - When a notification is dispatched, it's published to that channel
  - The manager listens on the channel and fans out to all WebSocket connections
    for that user on this instance (supports horizontal scaling)

                ┌─────────────────────────────────────────┐
                │           Notification Service           │
                │                                          │
  Task Svc ───► │  publish(user_id, payload)               │
                │         │                                │
                │         ▼                                │
                │  Redis: ws:user:{user_id}                │
                │         │                                │
                │         ├──► ws_instance_1 ──► Client A  │
                │         └──► ws_instance_2 ──► Client B  │
                └─────────────────────────────────────────┘
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.core.config import settings

logger = logging.getLogger(__name__)

# user_id → set of active WebSocket connections on THIS instance
_connections: dict[str, set[WebSocket]] = defaultdict(set)


class ConnectionManager:
    def __init__(self):
        self._redis: aioredis.Redis | None = None
        self._pubsub_task: asyncio.Task | None = None

    async def startup(self) -> None:
        """Called on app startup — connect to Redis and start the listener."""
        self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        self._pubsub_task = asyncio.create_task(self._pubsub_listener())
        logger.info("WebSocket manager started — connected to Redis.")

    async def shutdown(self) -> None:
        """Called on app shutdown — cancel listener and close Redis."""
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
        if self._redis:
            await self._redis.aclose()
        logger.info("WebSocket manager shut down.")

    # ── Connection lifecycle ──────────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        _connections[user_id].add(websocket)
        logger.info("WS connected: user=%s total_conns=%d", user_id, len(_connections[user_id]))

        # Send a welcome handshake
        await websocket.send_json({
            "event": "connected",
            "user_id": user_id,
            "message": "Real-time notifications active.",
        })

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        _connections[user_id].discard(websocket)
        if not _connections[user_id]:
            del _connections[user_id]
        logger.info("WS disconnected: user=%s remaining=%d", user_id, len(_connections.get(user_id, set())))

    # ── Publishing ────────────────────────────────────────────────────────────────

    async def publish(self, user_id: str, payload: dict) -> None:
        """
        Publish a notification to the Redis channel for user_id.
        All service instances subscribed to that channel will relay it to connected clients.
        """
        if self._redis is None:
            logger.warning("Redis not connected — cannot publish notification.")
            return
        channel = f"ws:user:{user_id}"
        await self._redis.publish(channel, json.dumps(payload))

    # ── Pub/Sub listener ──────────────────────────────────────────────────────────

    async def _pubsub_listener(self) -> None:
        """
        Long-running coroutine that listens on Redis pub/sub pattern
        ws:user:* and relays messages to local WebSocket connections.
        """
        pubsub = self._redis.pubsub()
        await pubsub.psubscribe("ws:user:*")
        logger.info("Redis pub/sub listener started on pattern ws:user:*")

        async for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue
            try:
                # Channel format: ws:user:{user_id}
                channel: str = message["channel"]
                user_id = channel.removeprefix("ws:user:")
                payload = json.loads(message["data"])
                await self._broadcast_to_user(user_id, payload)
            except Exception as exc:
                logger.error("Error processing pub/sub message: %s", exc)

    async def _broadcast_to_user(self, user_id: str, payload: dict) -> None:
        """Send payload to all WebSocket connections for user_id on this instance."""
        sockets = _connections.get(user_id, set())
        if not sockets:
            return

        dead: list[WebSocket] = []
        for ws in list(sockets):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)

        # Clean up closed connections
        for ws in dead:
            _connections[user_id].discard(ws)

    # ── Direct send (same instance shortcut) ─────────────────────────────────────

    async def send_direct(self, user_id: str, payload: dict) -> None:
        """Bypass Redis — send directly to connections on this instance (dev/single node)."""
        await self._broadcast_to_user(user_id, payload)

    @property
    def online_users(self) -> list[str]:
        """Return list of user_ids with active connections on this instance."""
        return list(_connections.keys())

    def connection_count(self, user_id: str) -> int:
        return len(_connections.get(user_id, set()))


# Singleton instance shared across the app
manager = ConnectionManager()
