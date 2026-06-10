from collections.abc import Generator
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.runtime_settings import RuntimeSettingsService, get_runtime_settings_service
from app.main import app
from app.models.amazon_data import AmazonProductData
from app.models.product import Product
from app.routers import products as products_router


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[TestClient, sessionmaker], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    settings_file = tmp_path / "runtime_settings.json"

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def runtime_settings() -> RuntimeSettingsService:
        return RuntimeSettingsService(settings_file)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_runtime_settings_service] = runtime_settings
    monkeypatch.setattr(products_router, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(products_router, "RuntimeSettingsService", lambda: RuntimeSettingsService(settings_file))

    try:
        yield TestClient(app), TestingSessionLocal
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_get_scoring_defaults(client: tuple[TestClient, sessionmaker]) -> None:
    test_client, _ = client

    response = test_client.get("/settings/scoring")

    assert response.status_code == 200
    assert response.json() == {
        "profitability": 0.3,
        "roi": 0.2,
        "sales": 0.2,
        "price_stability": 0.15,
        "sellers": 0.1,
        "data_quality": 0.05,
    }


def test_put_scoring_accepts_valid_weights(client: tuple[TestClient, sessionmaker]) -> None:
    test_client, _ = client
    payload = {
        "profitability": 0.25,
        "roi": 0.25,
        "sales": 0.20,
        "price_stability": 0.15,
        "sellers": 0.10,
        "data_quality": 0.05,
    }

    response = test_client.put("/settings/scoring", json=payload)

    assert response.status_code == 200
    assert response.json() == payload
    assert test_client.get("/settings/scoring").json() == payload


def test_put_scoring_rejects_missing_non_positive_and_bad_sum(client: tuple[TestClient, sessionmaker]) -> None:
    test_client, _ = client
    valid = {
        "profitability": 0.30,
        "roi": 0.20,
        "sales": 0.20,
        "price_stability": 0.15,
        "sellers": 0.10,
        "data_quality": 0.05,
    }

    missing = dict(valid)
    missing.pop("roi")
    assert test_client.put("/settings/scoring", json=missing).status_code == 400

    non_positive = dict(valid)
    non_positive["roi"] = 0
    assert test_client.put("/settings/scoring", json=non_positive).json()["error"] == "roi must be positive."

    bad_sum = dict(valid)
    bad_sum["roi"] = 0.30
    assert test_client.put("/settings/scoring", json=bad_sum).json()["error"] == "Scoring weights must sum to 1.0."


def test_get_and_put_fee_settings(client: tuple[TestClient, sessionmaker]) -> None:
    test_client, _ = client
    payload = {
        "referral_fee_rate": 0.10,
        "default_fba_fee": 3.00,
        "default_shipping_cost": 0.50,
        "default_prep_fee": 0.25,
        "default_other_costs": 0.25,
    }

    assert test_client.get("/settings/fees").json()["referral_fee_rate"] == 0.15
    response = test_client.put("/settings/fees", json=payload)

    assert response.status_code == 200
    assert response.json() == payload
    invalid = dict(payload)
    invalid["default_fba_fee"] = -1
    assert test_client.put("/settings/fees", json=invalid).status_code == 400


def test_fee_settings_are_used_by_product_analysis(client: tuple[TestClient, sessionmaker]) -> None:
    test_client, TestingSessionLocal = client
    with TestingSessionLocal() as db:
        product = Product(product_name="Widget", upc="123", supplier_cost=Decimal("10.00"), status="enriched")
        db.add(product)
        db.flush()
        db.add(AmazonProductData(product_id=product.id, current_price=Decimal("25.00"), sellers_count=4, estimated_sales=1000))
        db.commit()
        product_id = product.id

    response = test_client.put(
        "/settings/fees",
        json={
            "referral_fee_rate": 0.10,
            "default_fba_fee": 3.00,
            "default_shipping_cost": 0.50,
            "default_prep_fee": 0.25,
            "default_other_costs": 0.25,
        },
    )
    assert response.status_code == 200

    assert test_client.post("/products/analyze", json={"product_ids": [product_id]}).status_code == 200

    detail = test_client.get(f"/products/{product_id}/analysis").json()
    assert detail["financial_analysis"]["referral_fee"] == 2.5
    assert detail["financial_analysis"]["fba_fee"] == 3.0
    assert detail["financial_analysis"]["net_profit"] == 8.5
