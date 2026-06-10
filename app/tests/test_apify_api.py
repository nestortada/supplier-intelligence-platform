from collections.abc import Generator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.amazon_data import AmazonProductData
from app.models.product import Product
from app.routers import products as products_router


class FakeApifyService:
    def __init__(self, item: dict | None = None) -> None:
        self.item = item
        self.calls: list[int] = []

    def search_amazon_product(self, product: Product) -> dict | None:
        self.calls.append(product.id)
        return self.item


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[TestClient, sessionmaker, FakeApifyService], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    fake_service = FakeApifyService({"asin": "B001", "title": "Amazon Widget", "price": "$12.50"})

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[products_router.get_apify_service] = lambda: fake_service
    monkeypatch.setattr(products_router, "SessionLocal", TestingSessionLocal)

    try:
        yield TestClient(app), TestingSessionLocal, fake_service
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_enrich_apify_creates_job_and_enriches_product(
    client: tuple[TestClient, sessionmaker, FakeApifyService],
) -> None:
    test_client, TestingSessionLocal, fake_service = client
    with TestingSessionLocal() as db:
        product = Product(product_name="Widget", upc="123", status="pending_analysis")
        db.add(product)
        db.commit()
        product_id = product.id

    response = test_client.post("/products/enrich-apify", json={"product_ids": [product_id]})

    assert response.status_code == 200
    assert response.json()["job_id"] == 1
    assert fake_service.calls == [product_id]

    job_response = test_client.get("/jobs/1")
    assert job_response.status_code == 200
    job_json = job_response.json()
    assert job_json["created_at"]
    assert job_json["updated_at"]
    assert {key: job_json[key] for key in (
        "job_id",
        "type",
        "status",
        "progress",
        "total_items",
        "processed_items",
        "failed_items",
        "error_message",
    )} == {
        "job_id": 1,
        "type": "apify_enrichment",
        "status": "completed",
        "progress": 100,
        "total_items": 1,
        "processed_items": 1,
        "failed_items": 0,
        "error_message": None,
    }

    with TestingSessionLocal() as db:
        product = db.get(Product, product_id)
        assert product.status == "enriched"
        assert db.query(AmazonProductData).filter(AmazonProductData.product_id == product_id).count() == 1


def test_enrich_apify_all_pending_selects_pending_products(
    client: tuple[TestClient, sessionmaker, FakeApifyService],
) -> None:
    test_client, TestingSessionLocal, fake_service = client
    with TestingSessionLocal() as db:
        db.add(Product(product_name="Pending", status="pending_analysis"))
        db.add(Product(product_name="Already enriched", status="enriched"))
        db.commit()

    response = test_client.post("/products/enrich-apify", json={"all_pending": True})

    assert response.status_code == 200
    assert response.json()["total_items"] == 1
    assert len(fake_service.calls) == 1


def test_enrich_apify_skips_recent_amazon_data_without_force_refresh(
    client: tuple[TestClient, sessionmaker, FakeApifyService],
) -> None:
    test_client, TestingSessionLocal, fake_service = client
    with TestingSessionLocal() as db:
        product = Product(product_name="Widget", status="pending_analysis")
        db.add(product)
        db.flush()
        db.add(AmazonProductData(product_id=product.id, asin="RECENT", captured_at=datetime.utcnow()))
        db.commit()
        product_id = product.id

    response = test_client.post("/products/enrich-apify", json={"product_ids": [product_id]})

    assert response.status_code == 200
    assert fake_service.calls == []
    assert test_client.get("/jobs/1").json()["processed_items"] == 1


def test_enrich_apify_force_refresh_ignores_recent_amazon_data(
    client: tuple[TestClient, sessionmaker, FakeApifyService],
) -> None:
    test_client, TestingSessionLocal, fake_service = client
    with TestingSessionLocal() as db:
        product = Product(product_name="Widget", status="pending_analysis")
        db.add(product)
        db.flush()
        db.add(AmazonProductData(product_id=product.id, asin="RECENT", captured_at=datetime.utcnow()))
        db.commit()
        product_id = product.id

    response = test_client.post("/products/enrich-apify", json={"product_ids": [product_id], "force_refresh": True})

    assert response.status_code == 200
    assert fake_service.calls == [product_id]


def test_enrich_apify_marks_no_result_as_insufficient_data(
    client: tuple[TestClient, sessionmaker, FakeApifyService],
) -> None:
    test_client, TestingSessionLocal, fake_service = client
    fake_service.item = None
    with TestingSessionLocal() as db:
        product = Product(product_name="Widget", status="pending_analysis")
        db.add(product)
        db.commit()
        product_id = product.id

    response = test_client.post("/products/enrich-apify", json={"product_ids": [product_id]})

    assert response.status_code == 200
    with TestingSessionLocal() as db:
        assert db.get(Product, product_id).status == "insufficient_data"


def test_enrich_apify_requires_product_ids_or_all_pending(
    client: tuple[TestClient, sessionmaker, FakeApifyService],
) -> None:
    test_client, _, _ = client

    response = test_client.post("/products/enrich-apify", json={})

    assert response.status_code == 400
