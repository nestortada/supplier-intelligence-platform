from datetime import datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.realtime import publish_realtime_event


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookEventRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=120)
    profile_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class WebhookEventResponse(BaseModel):
    success: bool
    event_type: str
    profile_id: int | None = None
    received_at: datetime


@router.post("/events", response_model=WebhookEventResponse)
async def receive_webhook_event(
    payload: WebhookEventRequest,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
) -> WebhookEventResponse:
    if settings.WEBHOOK_SECRET and x_webhook_secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret.")

    received_at = datetime.utcnow()
    await publish_realtime_event(
        "webhook.received",
        {
            "event_type": payload.event_type,
            "payload": payload.payload,
            "received_at": received_at.isoformat(),
        },
        payload.profile_id,
    )
    return WebhookEventResponse(success=True, event_type=payload.event_type, profile_id=payload.profile_id, received_at=received_at)
