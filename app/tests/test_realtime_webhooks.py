from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_webhook_broadcasts_to_profile_socket(client: TestClient) -> None:
    with client.websocket_connect("/ws/realtime?profile_id=1") as websocket:
        connected = websocket.receive_json()
        assert connected["type"] == "realtime.connected"

        response = client.post(
            "/webhooks/events",
            json={"event_type": "external.product.changed", "profile_id": 1, "payload": {"product_id": 10}},
        )
        assert response.status_code == 200

        event = websocket.receive_json()
        assert event["type"] == "webhook.received"
        assert event["profile_id"] == 1
        assert event["payload"]["event_type"] == "external.product.changed"
        assert event["payload"]["payload"] == {"product_id": 10}


def test_webhook_secret_is_enforced(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "WEBHOOK_SECRET", "secret")

    unauthorized = client.post(
        "/webhooks/events",
        json={"event_type": "external.product.changed", "payload": {}},
    )
    assert unauthorized.status_code == 401

    authorized = client.post(
        "/webhooks/events",
        headers={"X-Webhook-Secret": "secret"},
        json={"event_type": "external.product.changed", "payload": {}},
    )
    assert authorized.status_code == 200
