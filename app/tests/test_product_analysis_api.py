import json
from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.product_schema import ensure_product_selection_schema
from app.main import app
from app.models.amazon_data import AmazonProductData
from app.models.analysis import ProductAnalysis
from app.models.product import Product
from app.models.supplier import Supplier
from app.routers import products as products_router


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[TestClient, sessionmaker], None, None]:
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
    monkeypatch.setattr(products_router, "SessionLocal", TestingSessionLocal)

    try:
        yield TestClient(app), TestingSessionLocal
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def add_supplier_product(
    db: Session,
    supplier_name: str,
    product_name: str,
    supplier_cost: str,
    amazon_price: str,
    supplier_id: int | None = None,
    category: str = "Toys",
    upc: str | None = "123456789012",
    sellers_count: int | None = 4,
    estimated_sales: int | None = 1000,
    price_history: list | None = None,
    sellers_history: list | None = None,
) -> Product:
    if supplier_id is None:
        supplier = Supplier(supplier_name=supplier_name)
        db.add(supplier)
        db.flush()
        supplier_id = supplier.id

    product = Product(
        supplier_id=supplier_id,
        product_name=product_name,
        upc=upc,
        category=category,
        supplier_cost=Decimal(supplier_cost),
        status="enriched",
    )
    db.add(product)
    db.flush()
    db.add(
        AmazonProductData(
            product_id=product.id,
            asin=f"ASIN-{product.id}",
            amazon_title=f"Amazon {product_name}",
            current_price=Decimal(amazon_price),
            sellers_count=sellers_count,
            estimated_sales=estimated_sales,
            raw_response_json=json.dumps({"price_new_history": price_history or [amazon_price, amazon_price, amazon_price]}),
            price_history_json=json.dumps(price_history or [amazon_price, amazon_price, amazon_price]),
            sellers_history_json=json.dumps(sellers_history or [sellers_count]),
        )
    )
    return product


def test_analyze_products_with_ids_creates_job_analysis_and_updates_status(
    client: tuple[TestClient, sessionmaker],
) -> None:
    test_client, TestingSessionLocal = client
    with TestingSessionLocal() as db:
        product = add_supplier_product(db, "Acme", "Widget", "10.00", "25.00", price_history=[25, 25, 25])
        db.commit()
        product_id = product.id

    response = test_client.post("/products/analyze", json={"product_ids": [product_id]})

    assert response.status_code == 200
    assert response.json()["total_items"] == 1

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
        "type": "product_analysis",
        "status": "completed",
        "progress": 100,
        "total_items": 1,
        "processed_items": 1,
        "failed_items": 0,
        "error_message": None,
    }

    with TestingSessionLocal() as db:
        product = db.get(Product, product_id)
        analysis = db.query(ProductAnalysis).filter(ProductAnalysis.product_id == product_id).one()
        assert product.status == "buy"
        assert float(analysis.final_opportunity_score) == 85.5
        assert analysis.recommendation_status == "buy"


def test_analyze_products_all_true_analyzes_all_products(client: tuple[TestClient, sessionmaker]) -> None:
    test_client, TestingSessionLocal = client
    with TestingSessionLocal() as db:
        add_supplier_product(db, "Acme", "Widget", "10.00", "25.00")
        add_supplier_product(db, "Beta", "Gadget", "10.00", "15.00", category="Kitchen", estimated_sales=120)
        db.commit()

    response = test_client.post("/products/analyze", json={"all": True})

    assert response.status_code == 200
    assert response.json()["total_items"] == 2
    with TestingSessionLocal() as db:
        assert db.query(ProductAnalysis).count() == 2


def test_analyze_products_validates_payload(client: tuple[TestClient, sessionmaker]) -> None:
    test_client, _ = client

    assert test_client.post("/products/analyze", json={}).status_code == 400
    assert test_client.post("/products/analyze", json={"product_ids": [999]}).status_code == 404


def test_product_ranking_orders_products_and_applies_filters(client: tuple[TestClient, sessionmaker]) -> None:
    test_client, TestingSessionLocal = client
    with TestingSessionLocal() as db:
        supplier_one = Supplier(supplier_name="Acme")
        supplier_two = Supplier(supplier_name="Beta")
        db.add_all([supplier_one, supplier_two])
        db.flush()
        high = add_supplier_product(
            db,
            "Acme",
            "Strong Widget",
            "10.00",
            "25.00",
            supplier_id=supplier_one.id,
            category="Toys",
            sellers_count=4,
            estimated_sales=1000,
            price_history=[25, 25, 25],
        )
        low = add_supplier_product(
            db,
            "Beta",
            "Weak Gadget",
            "10.00",
            "15.00",
            supplier_id=supplier_two.id,
            category="Kitchen",
            upc=None,
            sellers_count=12,
            estimated_sales=120,
            price_history=[15, 15, 15],
        )
        db.commit()
        high_id = high.id
        low_id = low.id
        supplier_one_id = supplier_one.id

    assert test_client.post("/products/analyze", json={"all": True}).status_code == 200

    response = test_client.get("/products/ranking")
    assert response.status_code == 200
    ranking = response.json()
    assert [item["product"]["id"] for item in ranking] == [high_id, low_id]

    filtered = test_client.get(
        "/products/ranking",
        params={
            "min_score": 80,
            "status": "buy",
            "supplier_id": supplier_one_id,
            "category": "toy",
            "min_roi": 0.4,
            "min_margin": 0.15,
            "min_sales": 500,
            "sellers_min": 4,
            "sellers_max": 5,
        },
    )
    assert filtered.status_code == 200
    assert [item["product"]["id"] for item in filtered.json()] == [high_id]


def test_selected_products_update_performance_and_clear_without_deleting_data(
    client: tuple[TestClient, sessionmaker],
) -> None:
    test_client, TestingSessionLocal = client
    with TestingSessionLocal() as db:
        product = add_supplier_product(db, "Acme", "Widget", "10.00", "25.00")
        db.commit()
        product_id = product.id

    assert test_client.post("/products/analyze", json={"product_ids": [product_id]}).status_code == 200

    select_response = test_client.patch(
        f"/products/{product_id}/selection",
        json={"selected_for_sale": True, "sale_performance": None},
    )
    assert select_response.status_code == 200
    assert select_response.json()["product"]["selected_for_sale"] is True
    assert select_response.json()["product"]["selected_at"] is not None

    selected_response = test_client.get("/products/selected")
    assert selected_response.status_code == 200
    selected = selected_response.json()
    assert [item["product"]["id"] for item in selected] == [product_id]
    assert selected[0]["amazon_data"]["asin"] == f"ASIN-{product_id}"
    assert selected[0]["analysis"]["recommendation_status"] == "buy"
    assert selected[0]["sale_performance"] is None

    performance_response = test_client.patch(
        "/products/selected/performance",
        json={"product_id": product_id, "sale_performance": "medium"},
    )
    assert performance_response.status_code == 200
    assert performance_response.json()["product"]["sale_performance"] == "medium"

    invalid_response = test_client.patch(
        "/products/selected/performance",
        json={"product_id": product_id, "sale_performance": "excellent"},
    )
    assert invalid_response.status_code == 422

    clear_response = test_client.delete("/products/selected")
    assert clear_response.status_code == 200
    assert clear_response.json() == {"success": True, "updated": 1}
    assert test_client.get("/products/selected").json() == []

    with TestingSessionLocal() as db:
        product = db.get(Product, product_id)
        assert product is not None
        assert product.selected_for_sale is False
        assert product.sale_performance is None
        assert db.query(AmazonProductData).count() == 1
        assert db.query(ProductAnalysis).count() == 1


def test_product_selection_can_be_removed_with_product_endpoint(client: tuple[TestClient, sessionmaker]) -> None:
    test_client, TestingSessionLocal = client
    with TestingSessionLocal() as db:
        product = add_supplier_product(db, "Acme", "Widget", "10.00", "25.00")
        db.commit()
        product_id = product.id

    assert test_client.patch(f"/products/{product_id}/selection", json={"selected_for_sale": True}).status_code == 200

    remove_response = test_client.patch(
        f"/products/{product_id}/selection",
        json={"selected_for_sale": False, "sale_performance": "high"},
    )
    assert remove_response.status_code == 200
    removed = remove_response.json()["product"]
    assert removed["selected_for_sale"] is False
    assert removed["sale_performance"] is None
    assert removed["selected_at"] is None


def test_product_selection_schema_adds_columns_to_existing_sqlite_table() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE products (id INTEGER NOT NULL PRIMARY KEY, product_name VARCHAR(255))"))
        connection.execute(text("INSERT INTO products (id, product_name) VALUES (1, 'Legacy')"))

    ensure_product_selection_schema(engine)

    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(products)")).fetchall()}
        selected_for_sale = connection.execute(text("SELECT selected_for_sale FROM products WHERE id = 1")).scalar()

    assert {"selected_for_sale", "sale_performance", "selected_at"}.issubset(columns)
    assert selected_for_sale == 0


def test_product_analysis_detail_returns_financial_scores_recommendation_and_histories(
    client: tuple[TestClient, sessionmaker],
) -> None:
    test_client, TestingSessionLocal = client
    with TestingSessionLocal() as db:
        product = add_supplier_product(
            db,
            "Acme",
            "Widget",
            "10.00",
            "25.00",
            price_history=[24, 25, 25],
            sellers_history=[4, 5],
        )
        db.commit()
        product_id = product.id

    assert test_client.post("/products/analyze", json={"product_ids": [product_id]}).status_code == 200

    response = test_client.get(f"/products/{product_id}/analysis")

    assert response.status_code == 200
    detail = response.json()
    assert detail["product"]["id"] == product_id
    assert detail["amazon_data"]["asin"] == f"ASIN-{product_id}"
    assert detail["financial_analysis"]["net_profit"] == 5.0
    assert detail["scores"]["final_opportunity_score"] == 85.5
    assert detail["recommendation"]["status"] == "buy"
    assert detail["risks"] == []
    assert detail["price_history"] == [24.0, 25.0, 25.0]
    assert detail["price_history_metrics"]["has_price_history"] is True
    assert detail["sellers_history"] == [4, 5]


def test_product_analysis_detail_returns_404_when_analysis_is_missing(
    client: tuple[TestClient, sessionmaker],
) -> None:
    test_client, TestingSessionLocal = client
    with TestingSessionLocal() as db:
        product = Product(product_name="Unanalyzed")
        db.add(product)
        db.commit()
        product_id = product.id

    response = test_client.get(f"/products/{product_id}/analysis")

    assert response.status_code == 404


def test_clear_product_database_removes_products_amazon_data_and_analyses(
    client: tuple[TestClient, sessionmaker],
) -> None:
    test_client, TestingSessionLocal = client
    with TestingSessionLocal() as db:
        product = add_supplier_product(db, "Acme", "Widget", "10.00", "25.00")
        db.commit()
        product_id = product.id

    assert test_client.post("/products/analyze", json={"product_ids": [product_id]}).status_code == 200

    response = test_client.delete("/products/database")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "products_deleted": 1,
        "amazon_data_deleted": 1,
        "analyses_deleted": 1,
    }
    with TestingSessionLocal() as db:
        assert db.query(Product).count() == 0
        assert db.query(AmazonProductData).count() == 0
        assert db.query(ProductAnalysis).count() == 0
