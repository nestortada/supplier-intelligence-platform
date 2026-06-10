from collections.abc import Generator
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.email_campaign import EmailCampaign, EmailLog
from app.models.supplier import Supplier


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


def test_list_email_campaigns_supports_pagination_status_and_pending(client: TestClient) -> None:
    with next(app.dependency_overrides[get_db]()) as db:
        now = datetime.utcnow()
        db.add_all(
            [
                EmailCampaign(
                    subject="Old completed",
                    status="completed",
                    total_recipients=10,
                    sent_count=9,
                    failed_count=1,
                    created_at=now - timedelta(days=1),
                    updated_at=now - timedelta(days=1),
                ),
                EmailCampaign(
                    subject="New active",
                    status="in_progress",
                    total_recipients=8,
                    sent_count=3,
                    failed_count=1,
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        db.commit()

    response = client.get("/emails/campaigns", params={"page": 1, "page_size": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["items"][0]["subject"] == "New active"
    assert payload["items"][0]["pending"] == 4

    filtered_response = client.get("/emails/campaigns", params={"status": "completed"})

    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert filtered_payload["total"] == 1
    assert filtered_payload["items"][0]["status"] == "completed"


def test_cancel_campaign_marks_active_campaign_canceled(client: TestClient) -> None:
    with next(app.dependency_overrides[get_db]()) as db:
        campaign = EmailCampaign(
            subject="Cancelable",
            status="in_progress",
            total_recipients=5,
            sent_count=1,
            failed_count=0,
        )
        db.add(campaign)
        db.commit()
        campaign_id = campaign.id

    response = client.patch(f"/emails/campaigns/{campaign_id}/cancel")

    assert response.status_code == 200
    payload = response.json()
    assert payload["campaign_id"] == campaign_id
    assert payload["status"] == "canceled"
    assert payload["pending"] == 4


def test_list_eligible_suppliers_matches_campaign_rules(client: TestClient) -> None:
    with next(app.dependency_overrides[get_db]()) as db:
        db.add_all(
            [
                Supplier(supplier_name="Acme", email="sales@acme.test", is_valid_email=True, status="pending"),
                Supplier(supplier_name="Duplicate", email="SALES@acme.test", is_valid_email=True, status="pending"),
                Supplier(supplier_name="Already Sent", email="sent@example.test", is_valid_email=True, status="email_sent"),
                Supplier(supplier_name="Invalid", email="not-an-email", is_valid_email=True, status="pending"),
                Supplier(supplier_name="Unverified", email="lead@example.test", is_valid_email=False, status="pending"),
            ]
        )
        db.commit()

    response = client.get("/emails/eligible-suppliers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["email"].lower() == "sales@acme.test"


def test_list_email_logs_includes_supplier_display_fields(client: TestClient) -> None:
    with next(app.dependency_overrides[get_db]()) as db:
        supplier = Supplier(
            supplier_name="Apex Contact",
            company="Apex Manufacturing",
            email="sales@apex.test",
            is_valid_email=True,
        )
        db.add(supplier)
        db.flush()
        db.add(
            EmailLog(
                supplier_id=supplier.id,
                to_email=supplier.email,
                status="failed",
                error_message="EmailJS rejected the request.",
                provider_response="bad request",
            )
        )
        db.commit()

    response = client.get("/emails/logs")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["supplier_name"] == "Apex Contact"
    assert payload[0]["supplier_company"] == "Apex Manufacturing"
    assert payload[0]["error_message"] == "EmailJS rejected the request."
