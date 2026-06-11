from collections.abc import Generator
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.sync import SyncOutbox
from app.models.user_profile import UserProfile
from app.services.sync_registry import serialize_entity
from app.services.sync_service import SyncService


class FakeSyncClient:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str, str], dict[str, Any]] = {}

    def get_document(self, entity_type: str, profile_sync_id: str, sync_id: str) -> dict[str, Any] | None:
        return self.store.get((entity_type, profile_sync_id, sync_id))

    def set_document(self, entity_type: str, profile_sync_id: str, sync_id: str, payload: dict[str, Any]) -> None:
        self.store[(entity_type, profile_sync_id, sync_id)] = dict(payload)

    def iter_profiles(self) -> list[dict[str, Any]]:
        return [payload for (entity_type, _, _), payload in self.store.items() if entity_type == "user_profile"]

    def iter_documents(self, entity_type: str, profile_sync_id: str) -> list[dict[str, Any]]:
        return [
            payload
            for (stored_type, stored_profile_sync_id, _), payload in self.store.items()
            if stored_type == entity_type and stored_profile_sync_id == profile_sync_id
        ]


@pytest.fixture()
def db_session(monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    monkeypatch.setattr("app.services.sync_service.settings.FIREBASE_ENABLED", True)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_sync_payload_serializes_values_and_relationship_sync_ids(db_session: Session) -> None:
    profile = UserProfile(name="Nestor")
    supplier = Supplier(profile=profile, supplier_name="Acme")
    product = Product(profile=profile, supplier=supplier, product_name="Widget", supplier_cost=Decimal("12.50"))
    db_session.add_all([profile, supplier, product])
    db_session.flush()

    payload = serialize_entity(product, db_session)

    assert payload["entity_type"] == "product"
    assert payload["profile_sync_id"] == profile.sync_id
    assert payload["supplier_sync_id"] == supplier.sync_id
    assert payload["supplier_cost"] == 12.5
    assert isinstance(payload["created_at"], str)


def test_local_writes_create_outbox_entries(db_session: Session) -> None:
    profile = UserProfile(name="Nestor")
    supplier = Supplier(profile=profile, supplier_name="Acme")
    db_session.add_all([profile, supplier])
    db_session.commit()

    rows = db_session.query(SyncOutbox).order_by(SyncOutbox.id.asc()).all()

    assert [row.entity_type for row in rows] == ["user_profile", "supplier"]
    assert all(row.status == "pending" for row in rows)


def test_sync_pushes_local_newer_payload_to_remote(db_session: Session) -> None:
    fake = FakeSyncClient()
    profile = UserProfile(name="Nestor")
    supplier = Supplier(profile=profile, supplier_name="Local Supplier")
    db_session.add_all([profile, supplier])
    db_session.commit()

    SyncService(db_session, fake).run_once()

    remote = fake.get_document("supplier", profile.sync_id, supplier.sync_id)
    assert remote is not None
    assert remote["supplier_name"] == "Local Supplier"


def test_sync_applies_remote_newer_payload_over_local(db_session: Session) -> None:
    fake = FakeSyncClient()
    profile = UserProfile(name="Nestor")
    supplier = Supplier(profile=profile, supplier_name="Local Supplier")
    db_session.add_all([profile, supplier])
    db_session.commit()

    remote_payload = serialize_entity(supplier, db_session)
    remote_payload["supplier_name"] = "Remote Supplier"
    remote_payload["sync_updated_at"] = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    fake.set_document("supplier", profile.sync_id, supplier.sync_id, remote_payload)

    SyncService(db_session, fake).run_once()
    db_session.refresh(supplier)

    assert supplier.supplier_name == "Remote Supplier"


def test_sync_applies_newer_remote_delete(db_session: Session) -> None:
    fake = FakeSyncClient()
    profile = UserProfile(name="Nestor")
    supplier = Supplier(profile=profile, supplier_name="Delete Me")
    db_session.add_all([profile, supplier])
    db_session.commit()

    remote_payload = serialize_entity(supplier, db_session)
    remote_payload["sync_updated_at"] = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    remote_payload["sync_deleted_at"] = remote_payload["sync_updated_at"]
    fake.set_document("supplier", profile.sync_id, supplier.sync_id, remote_payload)

    SyncService(db_session, fake).run_once()

    assert db_session.query(Supplier).filter(Supplier.sync_id == supplier.sync_id).first() is None


def test_sync_api_status_and_manual_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.sync_service.settings.FIREBASE_ENABLED", True)
    fake = FakeSyncClient()
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

    monkeypatch.setattr("app.services.sync_service.get_sync_client", lambda: fake)
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestingSessionLocal() as db:
            db.add(UserProfile(name="Nestor"))
            db.commit()

        client = TestClient(app)
        status_response = client.get("/sync/status")
        run_response = client.post("/sync/run")

        assert status_response.status_code == 200
        assert status_response.json()["enabled"] is True
        assert run_response.status_code == 200
        assert run_response.json()["pending_count"] == 0
        assert fake.iter_profiles()
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
