from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.email_campaign import EmailCampaign, EmailLog
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


def test_upload_suppliers_creates_suppliers(client: TestClient) -> None:
    content = "Supplier,Email,Website\nAcme,sales@acme.test,https://acme.test\n"

    response = client.post(
        "/suppliers/upload",
        files={"file": ("suppliers.csv", content, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["suppliers_created"] == 1
    assert client.get("/suppliers").json()["total"] == 1


def test_upload_catalog_with_supplier_name_creates_supplier_and_products(client: TestClient) -> None:
    content = "Product,Vendor SKU,UPC Code,Wholesale Price\nWidget,A-1,123456789012,$12.50\n"

    response = client.post(
        "/catalogs/upload",
        data={"supplier_name": "Acme Supply"},
        files={"file": ("catalog.csv", content, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "products_detected": 1,
        "products_created": 1,
        "duplicates": 0,
        "missing_upc": 0,
        "errors": 0,
    }

    products_response = client.get("/products", params={"supplier_id": 1})
    assert products_response.status_code == 200
    assert products_response.json()["total"] == 1
    assert products_response.json()["items"][0]["status"] == "pending_analysis"


def test_upload_catalog_without_supplier_returns_400(client: TestClient) -> None:
    response = client.post(
        "/catalogs/upload",
        files={"file": ("catalog.csv", "Product,UPC\nWidget,123\n", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {
        "success": False,
        "error": "supplier_id or supplier_name is required.",
        "details": None,
    }


def test_upload_rejects_invalid_extension_with_standard_error(client: TestClient) -> None:
    response = client.post(
        "/suppliers/upload",
        files={"file": ("suppliers.txt", "Supplier,Email\nAcme,sales@acme.test\n", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json() == {
        "success": False,
        "error": "Invalid file format. Use .xlsx, .xls, or .csv.",
        "details": None,
    }


def test_upload_rejects_large_file_with_standard_error(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.excel_service.settings.MAX_UPLOAD_SIZE_MB", 0)

    response = client.post(
        "/catalogs/upload",
        data={"supplier_name": "Acme"},
        files={"file": ("catalog.csv", "Product,UPC\nWidget,123\n", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["success"] is False
    assert response.json()["error"] == "Uploaded file is too large. Maximum size is 0 MB."


def test_upload_catalog_counts_file_and_database_duplicates(client: TestClient) -> None:
    with next(app.dependency_overrides[get_db]()) as db:
        supplier = Supplier(supplier_name="Existing")
        db.add(supplier)
        db.flush()
        db.add(Product(supplier_id=supplier.id, product_name="Old", upc="111", sku="OLD"))
        db.commit()

    content = "Product,SKU,UPC\nDuplicate DB,A,111\nNew,B,222\nDuplicate File,C,222\n"
    response = client.post(
        "/catalogs/upload",
        data={"supplier_id": "1"},
        files={"file": ("catalog.csv", content, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["products_detected"] == 3
    assert response.json()["products_created"] == 1
    assert response.json()["duplicates"] == 2


def test_clear_supplier_database_removes_suppliers_products_and_email_history(client: TestClient) -> None:
    with next(app.dependency_overrides[get_db]()) as db:
        supplier = Supplier(supplier_name="Clear Me", email="sales@clear.test", is_valid_email=True)
        db.add(supplier)
        db.flush()
        db.add(Product(supplier_id=supplier.id, product_name="Widget"))
        db.add(EmailCampaign(subject="Campaign", status="completed", total_recipients=1, sent_count=1))
        db.add(EmailLog(supplier_id=supplier.id, to_email=supplier.email, status="sent"))
        db.commit()

    response = client.delete("/suppliers/database")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["suppliers_deleted"] == 1
    assert response.json()["products_deleted"] == 1
    assert response.json()["email_logs_deleted"] == 1
    assert response.json()["email_campaigns_deleted"] == 1
    assert client.get("/suppliers").json()["total"] == 0
    assert client.get("/emails/logs").json() == []


def test_bulk_update_status_accepts_valid_status(client: TestClient) -> None:
    with next(app.dependency_overrides[get_db]()) as db:
        supplier = Supplier(supplier_name="Bulk")
        db.add(supplier)
        db.flush()
        product = Product(supplier_id=supplier.id, product_name="Widget")
        db.add(product)
        db.commit()
        product_id = product.id

    response = client.post("/products/bulk-update-status", json={"product_ids": [product_id], "status": "review"})

    assert response.status_code == 200
    assert response.json() == {"success": True, "updated": 1}
    assert client.get(f"/products/{product_id}").json()["status"] == "review"


def test_bulk_update_status_rejects_invalid_status(client: TestClient) -> None:
    response = client.post("/products/bulk-update-status", json={"product_ids": [1], "status": "invalid"})

    assert response.status_code == 422
