import asyncio
import logging
from datetime import datetime
from threading import RLock
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState


logger = logging.getLogger(__name__)


class RealtimeConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int | None, set[WebSocket]] = {}
        self._lock = RLock()

    async def connect(self, websocket: WebSocket, profile_id: int | None) -> None:
        await websocket.accept()
        with self._lock:
            self._connections.setdefault(profile_id, set()).add(websocket)

    async def disconnect(self, websocket: WebSocket, profile_id: int | None) -> None:
        with self._lock:
            sockets = self._connections.get(profile_id)
            if sockets is None:
                return
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(profile_id, None)

    async def broadcast(self, event_type: str, payload: dict[str, Any] | None = None, profile_id: int | None = None) -> None:
        event = {
            "type": event_type,
            "profile_id": profile_id,
            "payload": payload or {},
            "created_at": datetime.utcnow().isoformat(),
        }

        with self._lock:
            targets = list(self._connections.get(profile_id, set()))
            if profile_id is not None:
                targets.extend(self._connections.get(None, set()))

        stale: list[tuple[WebSocket, int | None]] = []
        for websocket in targets:
            try:
                if websocket.client_state != WebSocketState.CONNECTED:
                    stale.append((websocket, profile_id))
                    continue
                await websocket.send_json(event)
            except Exception:
                logger.exception("realtime_broadcast_failed", extra={"event_type": event_type, "profile_id": profile_id})
                stale.append((websocket, profile_id))

        for websocket, stale_profile_id in stale:
            await self.disconnect(websocket, stale_profile_id)


manager = RealtimeConnectionManager()


async def publish_realtime_event(event_type: str, payload: dict[str, Any] | None = None, profile_id: int | None = None) -> None:
    await manager.broadcast(event_type, payload, profile_id)


def publish_realtime_event_sync(event_type: str, payload: dict[str, Any] | None = None, profile_id: int | None = None) -> None:
    try:
        asyncio.run(manager.broadcast(event_type, payload, profile_id))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(manager.broadcast(event_type, payload, profile_id))
