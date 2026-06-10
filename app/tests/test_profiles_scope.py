from collections.abc import Generator
from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.amazon_data import AmazonProductData
from app.models.analysis import ProductAnalysis
from app.models.background_job import BackgroundJob
from app.models.email_campaign import EmailCampaign, EmailLog
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.user_profile import UserProfile


def client_fixture() -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
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
        yield TestClient(app), TestingSessionLocal
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def seed_two_profiles(TestingSessionLocal: sessionmaker[Session]) -> tuple[int, int, int, int]:
    with TestingSessionLocal() as db:
        default_profile = UserProfile(name="Alex Mercer")
        second_profile = UserProfile(name="Jane Doe")
        db.add_all([default_profile, second_profile])
        db.flush()

        default_supplier = Supplier(profile_id=default_profile.id, supplier_name="Default Supply", email="default@example.test", is_valid_email=True)
        second_supplier = Supplier(profile_id=second_profile.id, supplier_name="Second Supply", email="second@example.test", is_valid_email=True)
        db.add_all([default_supplier, second_supplier])
        db.flush()

        default_product = Product(profile_id=default_profile.id, supplier_id=default_supplier.id, product_name="Default Widget", status="buy")
        second_product = Product(profile_id=second_profile.id, supplier_id=second_supplier.id, product_name="Second Widget", status="buy")
        db.add_all([default_product, second_product])
        db.flush()

        db.add_all(
            [
                ProductAnalysis(
                    product_id=default_product.id,
                    roi=Decimal("0.50"),
                    margin=Decimal("0.20"),
                    final_opportunity_score=Decimal("90.00"),
                    recommendation_status="buy",
                ),
                ProductAnalysis(
                    product_id=second_product.id,
                    roi=Decimal("0.10"),
                    margin=Decimal("0.05"),
                    final_opportunity_score=Decimal("55.00"),
                    recommendation_status="buy",
                ),
                EmailCampaign(profile_id=default_profile.id, subject="Default Campaign", status="completed", total_recipients=1, sent_count=1),
                EmailCampaign(profile_id=second_profile.id, subject="Second Campaign", status="completed", total_recipients=1, sent_count=1),
                EmailLog(profile_id=default_profile.id, supplier_id=default_supplier.id, to_email=default_supplier.email, status="sent", sent_at=datetime.utcnow()),
                EmailLog(profile_id=second_profile.id, supplier_id=second_supplier.id, to_email=second_supplier.email, status="sent", sent_at=datetime.utcnow()),
            ]
        )
        db.commit()
        return default_profile.id, second_profile.id, default_product.id, second_product.id


def test_profiles_can_be_listed_and_created() -> None:
    fixture = client_fixture()
    client, _ = next(fixture)
    try:
        response = client.get("/profiles")
        assert response.status_code == 200
        assert [profile["name"] for profile in response.json()] == ["Alex Mercer"]

        create_response = client.post("/profiles", json={"name": "Maria Rivera", "avatar_data_url": "data:image/png;base64,abc"})
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["name"] == "Maria Rivera"
        assert created["avatar_data_url"] == "data:image/png;base64,abc"

        list_response = client.get("/profiles")
        assert [profile["name"] for profile in list_response.json()] == ["Alex Mercer", "Maria Rivera"]
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass


def test_dashboard_email_and_product_data_are_scoped_by_profile() -> None:
    fixture = client_fixture()
    client, TestingSessionLocal = next(fixture)
    try:
        default_profile_id, second_profile_id, default_product_id, second_product_id = seed_two_profiles(TestingSessionLocal)

        default_headers = {"X-Profile-Id": str(default_profile_id)}
        second_headers = {"X-Profile-Id": str(second_profile_id)}

        default_summary = client.get("/dashboard/summary", headers=default_headers)
        second_summary = client.get("/dashboard/summary", headers=second_headers)
        assert default_summary.status_code == 200
        assert second_summary.status_code == 200
        assert default_summary.json()["products_uploaded"] == 1
        assert second_summary.json()["products_uploaded"] == 1

        default_ranking = client.get("/products/ranking", headers=default_headers).json()
        second_ranking = client.get("/products/ranking", headers=second_headers).json()
        assert [item["product"]["product_name"] for item in default_ranking] == ["Default Widget"]
        assert [item["product"]["product_name"] for item in second_ranking] == ["Second Widget"]

        assert client.get(f"/products/{second_product_id}/analysis", headers=default_headers).status_code == 404
        assert client.get(f"/products/{default_product_id}/analysis", headers=second_headers).status_code == 404

        default_campaigns = client.get("/emails/campaigns", headers=default_headers).json()
        second_campaigns = client.get("/emails/campaigns", headers=second_headers).json()
        assert [campaign["subject"] for campaign in default_campaigns["items"]] == ["Default Campaign"]
        assert [campaign["subject"] for campaign in second_campaigns["items"]] == ["Second Campaign"]
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass


def test_supplier_upload_and_listing_use_active_profile() -> None:
    fixture = client_fixture()
    client, _ = next(fixture)
    try:
        first_profile = client.post("/profiles", json={"name": "First"}).json()
        second_profile = client.post("/profiles", json={"name": "Second"}).json()

        upload = client.post(
            "/suppliers/upload",
            files={"file": ("suppliers.csv", b"supplier_name,email\nAcme,sales@acme.test\n", "text/csv")},
            headers={"X-Profile-Id": str(second_profile["id"])},
        )
        assert upload.status_code == 200
        assert upload.json()["suppliers_created"] == 1

        first_suppliers = client.get("/suppliers", headers={"X-Profile-Id": str(first_profile["id"])}).json()
        second_suppliers = client.get("/suppliers", headers={"X-Profile-Id": str(second_profile["id"])}).json()
        assert first_suppliers["total"] == 0
        assert second_suppliers["total"] == 1
        assert second_suppliers["items"][0]["supplier_name"] == "Acme"
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass


def test_patch_profile_updates_only_active_profile() -> None:
    fixture = client_fixture()
    client, _ = next(fixture)
    try:
        first_profile = client.post("/profiles", json={"name": "First"}).json()
        second_profile = client.post("/profiles", json={"name": "Second"}).json()

        forbidden = client.patch(
            f"/profiles/{second_profile['id']}",
            json={"name": "Blocked", "avatar_data_url": None},
            headers={"X-Profile-Id": str(first_profile["id"])},
        )
        assert forbidden.status_code == 403

        response = client.patch(
            f"/profiles/{first_profile['id']}",
            json={"name": "Updated First", "avatar_data_url": "data:image/png;base64,abc"},
            headers={"X-Profile-Id": str(first_profile["id"])},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated First"
        assert response.json()["avatar_data_url"] == "data:image/png;base64,abc"
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass


def test_delete_profile_removes_only_scoped_data() -> None:
    fixture = client_fixture()
    client, TestingSessionLocal = next(fixture)
    try:
        default_profile_id, second_profile_id, default_product_id, second_product_id = seed_two_profiles(TestingSessionLocal)
        with TestingSessionLocal() as db:
            db.add_all(
                [
                    AmazonProductData(product_id=default_product_id, asin="DEFAULT"),
                    AmazonProductData(product_id=second_product_id, asin="SECOND"),
                    BackgroundJob(profile_id=default_profile_id, type="default", status="completed"),
                    BackgroundJob(profile_id=second_profile_id, type="second", status="completed"),
                ]
            )
            db.commit()

        response = client.delete(f"/profiles/{default_profile_id}", headers={"X-Profile-Id": str(default_profile_id)})
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["active_profile"]["id"] == second_profile_id

        with TestingSessionLocal() as db:
            assert db.get(UserProfile, default_profile_id) is None
            assert db.get(UserProfile, second_profile_id) is not None
            assert db.query(Supplier).filter(Supplier.profile_id == default_profile_id).count() == 0
            assert db.query(Product).filter(Product.profile_id == default_profile_id).count() == 0
            assert db.query(EmailCampaign).filter(EmailCampaign.profile_id == default_profile_id).count() == 0
            assert db.query(EmailLog).filter(EmailLog.profile_id == default_profile_id).count() == 0
            assert db.query(BackgroundJob).filter(BackgroundJob.profile_id == default_profile_id).count() == 0
            assert db.query(ProductAnalysis).filter(ProductAnalysis.product_id == default_product_id).count() == 0
            assert db.query(AmazonProductData).filter(AmazonProductData.product_id == default_product_id).count() == 0
            assert db.query(Supplier).filter(Supplier.profile_id == second_profile_id).count() == 1
            assert db.query(Product).filter(Product.profile_id == second_profile_id).count() == 1
            assert db.query(ProductAnalysis).filter(ProductAnalysis.product_id == second_product_id).count() == 1
            assert db.query(AmazonProductData).filter(AmazonProductData.product_id == second_product_id).count() == 1
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass


def test_delete_last_profile_creates_empty_default_profile() -> None:
    fixture = client_fixture()
    client, _ = next(fixture)
    try:
        profile = client.get("/profiles").json()[0]
        response = client.delete(f"/profiles/{profile['id']}", headers={"X-Profile-Id": str(profile["id"])})

        assert response.status_code == 200
        active_profile = response.json()["active_profile"]
        assert active_profile["name"] == "Alex Mercer"

        profiles = client.get("/profiles").json()
        assert [profile["id"] for profile in profiles] == [active_profile["id"]]
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass
