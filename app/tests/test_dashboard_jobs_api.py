from collections.abc import Generator
from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.analysis import ProductAnalysis
from app.models.background_job import BackgroundJob
from app.models.email_campaign import EmailLog
from app.models.product import Product
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

    with TestingSessionLocal() as db:
        seed_dashboard_data(db)

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


def seed_dashboard_data(db: Session) -> None:
    supplier_one = Supplier(supplier_name="Acme", email="sales@acme.test", is_valid_email=True)
    supplier_two = Supplier(supplier_name="Beta", email="bad-email", is_valid_email=False)
    db.add_all([supplier_one, supplier_two])
    db.flush()

    product_one = Product(supplier_id=supplier_one.id, product_name="Buy Widget", status="buy")
    product_two = Product(supplier_id=supplier_one.id, product_name="Review Widget", status="review")
    product_three = Product(supplier_id=supplier_two.id, product_name="Discard Gadget", status="discard")
    db.add_all([product_one, product_two, product_three])
    db.flush()

    db.add_all(
        [
            ProductAnalysis(
                product_id=product_one.id,
                roi=Decimal("0.50"),
                margin=Decimal("0.20"),
                final_opportunity_score=Decimal("88.00"),
                recommendation_status="buy",
            ),
            ProductAnalysis(
                product_id=product_two.id,
                roi=Decimal("0.25"),
                margin=Decimal("0.12"),
                final_opportunity_score=Decimal("62.00"),
                recommendation_status="review",
            ),
            ProductAnalysis(
                product_id=product_three.id,
                roi=Decimal("-0.10"),
                margin=Decimal("-0.05"),
                final_opportunity_score=Decimal("20.00"),
                recommendation_status="discard",
            ),
        ]
    )
    db.add(EmailLog(supplier_id=supplier_one.id, to_email=supplier_one.email, status="sent", sent_at=datetime.utcnow()))
    db.add_all(
        [
            BackgroundJob(type="product_analysis", status="completed", progress=100, total_items=3, processed_items=3),
            BackgroundJob(type="apify_enrichment", status="failed", progress=50, total_items=2, processed_items=1, failed_items=1),
            BackgroundJob(type="apify_enrichment", status="in_progress", progress=25, total_items=4, processed_items=1),
        ]
    )
    db.commit()


def test_list_jobs_supports_filters_and_timestamps(client: TestClient) -> None:
    response = client.get("/jobs", params={"type": "product_analysis", "status": "completed"})

    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 1
    assert jobs[0]["type"] == "product_analysis"
    assert jobs[0]["status"] == "completed"
    assert jobs[0]["created_at"]
    assert jobs[0]["updated_at"]


def test_cancel_job_marks_active_job_canceled(client: TestClient) -> None:
    response = client.patch("/jobs/3/cancel")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == 3
    assert payload["status"] == "canceled"
    assert payload["progress"] == 100


def test_dashboard_summary(client: TestClient) -> None:
    response = client.get("/dashboard/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_suppliers": 2,
        "valid_emails": 1,
        "emails_sent": 1,
        "products_uploaded": 3,
        "products_analyzed": 3,
        "products_recommended": 1,
        "average_roi": pytest.approx(0.2166666667),
        "average_opportunity_score": pytest.approx(56.6666666667),
    }


def test_dashboard_top_opportunities(client: TestClient) -> None:
    response = client.get("/dashboard/top-opportunities", params={"limit": 2})

    assert response.status_code == 200
    rows = response.json()
    assert [row["product_name"] for row in rows] == ["Buy Widget", "Review Widget"]
    assert rows[0]["final_opportunity_score"] == 88.0


def test_dashboard_supplier_performance(client: TestClient) -> None:
    response = client.get("/dashboard/supplier-performance")

    assert response.status_code == 200
    assert response.json() == [{"supplier_id": 1, "supplier_name": "Acme", "recommended_products": 2}]
