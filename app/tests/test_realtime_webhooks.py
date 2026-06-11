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
        messages = [websocket.receive_json(), websocket.receive_json()]
        assert any(message["type"] == "realtime.connected" for message in messages)

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


def test_profile_presence_is_exposed_in_profiles_response(client: TestClient) -> None:
    response = client.get("/profiles")
    assert response.status_code == 200
    profile = response.json()[0]
    assert profile["is_online"] is False

    with client.websocket_connect(f"/ws/realtime?profile_id={profile['id']}") as websocket:
        messages = [websocket.receive_json(), websocket.receive_json()]
        assert any(message["type"] == "profile.presence" and message["payload"]["is_online"] is True for message in messages)

        online_response = client.get("/profiles")
        assert online_response.status_code == 200
        assert online_response.json()[0]["is_online"] is True

    offline_response = client.get("/profiles")
    assert offline_response.status_code == 200
    assert offline_response.json()[0]["is_online"] is False


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
