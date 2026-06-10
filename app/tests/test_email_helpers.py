from app.models.supplier import Supplier
from app.routers.emails import (
    build_template_params,
    dedupe_sendable_suppliers,
    is_supplier_sendable,
    normalize_template_id,
)


def test_build_template_params_uses_supplier_name_fallbacks() -> None:
    supplier = Supplier(
        email="sales@example.com",
        supplier_name=None,
        company="Example Co",
        category="Electronics",
        city="Miami",
        website="https://example.com",
    )

    params = build_template_params(supplier, "Subject")

    assert params["to_email"] == "sales@example.com"
    assert params["email"] == "sales@example.com"
    assert params["supplier_name"] == "Example Co"
    assert params["subject"] == "Subject"
    assert "latest product catalog" in (params["message"] or "")
    assert params["menssage"] == params["message"]


def test_build_template_params_defaults_supplier_name_to_there() -> None:
    supplier = Supplier(email="sales@example.com", supplier_name=None, company=None)

    params = build_template_params(supplier, "Subject")

    assert params["supplier_name"] == "there"


def test_is_supplier_sendable_requires_valid_email_flags() -> None:
    valid_supplier = Supplier(email="sales@example.com", is_valid_email=True)
    invalid_supplier = Supplier(email="not-an-email", is_valid_email=True)
    unverified_supplier = Supplier(email="sales@example.com", is_valid_email=False)

    assert is_supplier_sendable(valid_supplier)
    assert not is_supplier_sendable(invalid_supplier)
    assert not is_supplier_sendable(unverified_supplier)


def test_dedupe_sendable_suppliers_by_normalized_email() -> None:
    suppliers = [
        Supplier(id=1, email="SALES@example.com", is_valid_email=True),
        Supplier(id=2, email="sales@example.com", is_valid_email=True),
        Supplier(id=3, email="other@example.com", is_valid_email=True),
        Supplier(id=4, email="invalid", is_valid_email=True),
    ]

    deduped = dedupe_sendable_suppliers(suppliers)

    assert [supplier.id for supplier in deduped] == [1, 3]


def test_normalize_template_id_ignores_swagger_placeholders() -> None:
    assert normalize_template_id(None) is None
    assert normalize_template_id("optional_template_id") is None
    assert normalize_template_id(" string ") is None
    assert normalize_template_id("template_real123") == "template_real123"
