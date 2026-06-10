import pandas as pd

from app.services.excel_service import parse_products_dataframe, parse_suppliers_dataframe


def test_parse_suppliers_dataframe_removes_duplicate_emails_case_insensitive() -> None:
    dataframe = pd.DataFrame(
        [
            {"Supplier": "First", "Email": "SALES@example.com"},
            {"Supplier": "Duplicate", "Email": "sales@example.com"},
            {"Supplier": "Second", "Email": "contact@example.com"},
        ]
    )

    result = parse_suppliers_dataframe(dataframe)

    assert result.total_rows == 3
    assert result.duplicates_removed == 1
    assert len(result.rows) == 2
    assert result.valid_emails == 2
    assert {row["email"] for row in result.rows} == {"sales@example.com", "contact@example.com"}


def test_parse_products_dataframe_maps_catalog_columns_and_cleans_values() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "Item Description": "Widget",
                "Vendor SKU": " SKU-001 ",
                "UPC Code": "123-456.0",
                "EAN Code": " 987 654 ",
                "GTIN Code": "00-111",
                "Brand": "Acme",
                "Department": "Tools",
                "Wholesale Price": "$1,234.50",
                "Case Qty": "12.0",
                "Unit": "case",
            }
        ]
    )

    result = parse_products_dataframe(dataframe)

    assert result.products_detected == 1
    assert result.column_mapping["product_name"] == "Item Description"
    assert result.column_mapping["sku"] == "Vendor SKU"
    row = result.rows[0]
    assert row["product_name"] == "Widget"
    assert row["sku"] == "SKU-001"
    assert row["upc"] == "1234560"
    assert row["ean"] == "987654"
    assert row["gtin"] == "00111"
    assert row["supplier_cost"] == 1234.5
    assert row["case_quantity"] == 12
    assert row["status"] == "pending_analysis"
    assert "Item Description" in row["raw_row_json"]


def test_parse_products_dataframe_maps_amazon_identifier_columns_to_sku() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "Product": "MacBook",
                "Amazon URL": "https://www.amazon.com/Apple-2025-MacBook-15-inch-Laptop/dp/B0DZDBDCFH/",
                "Wholesale Price": "799",
            },
            {
                "Product": "Accessory",
                "ASIN": "B0BN72FYFG",
                "Wholesale Price": "12.50",
            },
        ]
    )

    result = parse_products_dataframe(dataframe)

    assert result.products_detected == 2
    assert result.rows[0]["sku"] == "https://www.amazon.com/Apple-2025-MacBook-15-inch-Laptop/dp/B0DZDBDCFH/"
    assert result.rows[1]["sku"] == "B0BN72FYFG"


def test_parse_products_dataframe_skips_rows_without_name_or_identifiers() -> None:
    dataframe = pd.DataFrame([{"Product Name": "", "UPC": "", "SKU": ""}, {"Product Name": "Valid"}])

    result = parse_products_dataframe(dataframe)

    assert result.skipped_empty_rows == 1
    assert result.products_detected == 1
    assert len(result.rows) == 1


def test_parse_products_dataframe_detects_duplicate_identifiers() -> None:
    dataframe = pd.DataFrame(
        [
            {"Product": "First", "UPC": "111", "SKU": "A"},
            {"Product": "Duplicate UPC", "UPC": "111", "SKU": "B"},
            {"Product": "Duplicate SKU", "UPC": "222", "SKU": "A"},
            {"Product": "Second", "UPC": "333", "SKU": "C"},
        ]
    )

    result = parse_products_dataframe(dataframe)

    assert result.products_detected == 4
    assert result.duplicates_removed == 2
    assert len(result.rows) == 2
    assert {row["product_name"] for row in result.rows} == {"First", "Second"}
