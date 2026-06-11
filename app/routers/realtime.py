from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.realtime import manager


router = APIRouter(tags=["realtime"])


@router.websocket("/ws/realtime")
async def realtime_socket(websocket: WebSocket, profile_id: int | None = None) -> None:
    await manager.connect(websocket, profile_id)
    try:
        await websocket.send_json(
            {
                "type": "realtime.connected",
                "profile_id": profile_id,
                "payload": {"message": "connected"},
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, profile_id)
    except Exception:
        await manager.disconnect(websocket, profile_id)
        raise
