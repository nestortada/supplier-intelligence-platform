from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import UploadFile

from app.core.config import settings
from app.utils.column_mapper import map_columns, normalize_column_name
from app.utils.validators import clean_ean, clean_price, clean_text, clean_upc, is_valid_email, normalize_email


SUPPORTED_EXTENSIONS = {".csv", ".xls", ".xlsx"}
SUPPLIER_FIELDS = (
    "supplier_name",
    "company",
    "email",
    "website",
    "phone",
    "city",
    "country",
    "category",
)
PRODUCT_COLUMN_ALIASES = {
    "product_name": ["product", "product name", "name", "item", "description", "item description"],
    "description": ["description", "long description", "details"],
    "sku": [
        "sku",
        "item code",
        "item_code",
        "code",
        "product code",
        "vendor sku",
        "asin",
        "amazon asin",
        "amazon url",
        "amazon link",
        "amazon product url",
        "product url",
    ],
    "upc": ["upc", "upc code", "barcode", "barcode number"],
    "ean": ["ean", "ean code"],
    "gtin": ["gtin", "gtin code"],
    "brand": ["brand", "manufacturer"],
    "category": ["category", "department", "type"],
    "supplier_cost": ["cost", "price", "wholesale price", "unit price", "supplier price"],
    "case_quantity": ["case quantity", "case qty", "pack", "qty", "quantity"],
    "uom": ["uom", "unit", "unit of measure"],
}
PRODUCT_FIELDS = tuple(PRODUCT_COLUMN_ALIASES)


class SupplierFileError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass
class ParsedSuppliersFile:
    rows: list[dict[str, Any]]
    total_rows: int
    valid_emails: int
    invalid_emails: int
    duplicates_removed: int
    skipped_empty_rows: int


@dataclass
class ParsedProductsFile:
    rows: list[dict[str, Any]]
    total_rows: int
    products_detected: int
    duplicates_removed: int
    skipped_empty_rows: int
    missing_upc: int
    errors: int
    column_mapping: dict[str, str]


def _has_useful_data(row: dict[str, Any]) -> bool:
    return any(row.get(field) for field in SUPPLIER_FIELDS)


def _map_product_columns(headers: list[Any]) -> dict[str, str]:
    normalized_headers = {normalize_column_name(header): str(header) for header in headers}
    mapped: dict[str, str] = {}

    for field_name, aliases in PRODUCT_COLUMN_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_column_name(alias)
            if normalized_alias in normalized_headers:
                mapped[field_name] = normalized_headers[normalized_alias]
                break

    return mapped


def _json_safe_value(value: Any) -> Any:
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass

    return value.item() if hasattr(value, "item") else value


def _clean_case_quantity(value: Any) -> int | None:
    text = clean_text(value)
    if text is None:
        return None

    try:
        return int(float(text.replace(",", "")))
    except ValueError:
        return None


def _has_product_identity(row: dict[str, Any]) -> bool:
    return bool(row.get("product_name") or row.get("upc") or row.get("ean") or row.get("gtin") or row.get("sku"))


def _supplier_status(row: dict[str, Any]) -> str:
    email = row.get("email")
    has_identity = bool(row.get("supplier_name") or row.get("company"))

    if not email or not has_identity:
        return "pending"

    if is_valid_email(email):
        return "valid_email"

    return "invalid_email"


async def read_uploaded_file(upload_file: UploadFile) -> pd.DataFrame:
    filename = upload_file.filename or ""
    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise SupplierFileError("Invalid file format. Use .xlsx, .xls, or .csv.")

    content = await upload_file.read()
    if not content:
        raise SupplierFileError("Uploaded file is empty.")
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise SupplierFileError(f"Uploaded file is too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB.")

    buffer = BytesIO(content)

    try:
        if extension == ".csv":
            return pd.read_csv(buffer, dtype=str)
        return pd.read_excel(buffer, dtype=str)
    except Exception as exc:
        raise SupplierFileError("Error reading supplier file.") from exc


def parse_suppliers_dataframe(dataframe: pd.DataFrame) -> ParsedSuppliersFile:
    if dataframe.empty:
        raise SupplierFileError("Uploaded file is empty.")

    column_mapping = map_columns(dataframe.columns)
    if "email" not in column_mapping:
        raise SupplierFileError("No email column found in uploaded file.")

    rows: list[dict[str, Any]] = []
    seen_emails: set[str] = set()
    duplicates_removed = 0
    skipped_empty_rows = 0

    for _, source_row in dataframe.iterrows():
        supplier_row: dict[str, Any] = {}

        for field in SUPPLIER_FIELDS:
            source_column = column_mapping.get(field)
            raw_value = source_row.get(source_column) if source_column else None
            supplier_row[field] = clean_text(raw_value)

        supplier_row["email"] = normalize_email(supplier_row.get("email"))

        if not _has_useful_data(supplier_row):
            skipped_empty_rows += 1
            continue

        email = supplier_row.get("email")
        if email:
            if email in seen_emails:
                duplicates_removed += 1
                continue
            seen_emails.add(email)

        supplier_row["is_valid_email"] = is_valid_email(email)
        supplier_row["status"] = _supplier_status(supplier_row)
        rows.append(supplier_row)

    valid_emails = sum(1 for row in rows if row.get("email") and row.get("is_valid_email"))
    invalid_emails = sum(1 for row in rows if row.get("email") and not row.get("is_valid_email"))

    return ParsedSuppliersFile(
        rows=rows,
        total_rows=len(dataframe.index),
        valid_emails=valid_emails,
        invalid_emails=invalid_emails,
        duplicates_removed=duplicates_removed,
        skipped_empty_rows=skipped_empty_rows,
    )


async def parse_suppliers_file(upload_file: UploadFile) -> ParsedSuppliersFile:
    dataframe = await read_uploaded_file(upload_file)
    return parse_suppliers_dataframe(dataframe)


def parse_products_dataframe(dataframe: pd.DataFrame) -> ParsedProductsFile:
    if dataframe.empty:
        raise SupplierFileError("Uploaded file is empty.")

    column_mapping = _map_product_columns(list(dataframe.columns))
    rows: list[dict[str, Any]] = []
    seen_upc: set[str] = set()
    seen_ean: set[str] = set()
    seen_gtin: set[str] = set()
    seen_sku: set[str] = set()
    duplicates_removed = 0
    skipped_empty_rows = 0
    errors = 0

    for _, source_row in dataframe.iterrows():
        try:
            product_row: dict[str, Any] = {}

            for field in PRODUCT_FIELDS:
                source_column = column_mapping.get(field)
                raw_value = source_row.get(source_column) if source_column else None
                if field == "sku" and clean_text(raw_value) is None:
                    sku_aliases = {normalize_column_name(alias) for alias in PRODUCT_COLUMN_ALIASES["sku"]}
                    for column in dataframe.columns:
                        if source_column and column == source_column:
                            continue
                        if normalize_column_name(column) in sku_aliases and clean_text(source_row.get(column)) is not None:
                            raw_value = source_row.get(column)
                            break

                if field in {"upc", "gtin"}:
                    product_row[field] = clean_upc(raw_value)
                elif field == "ean":
                    product_row[field] = clean_ean(raw_value)
                elif field == "supplier_cost":
                    product_row[field] = clean_price(raw_value)
                elif field == "case_quantity":
                    product_row[field] = _clean_case_quantity(raw_value)
                else:
                    product_row[field] = clean_text(raw_value)

            if not _has_product_identity(product_row):
                skipped_empty_rows += 1
                continue

            duplicate = False
            for key, seen_values in (
                ("upc", seen_upc),
                ("ean", seen_ean),
                ("gtin", seen_gtin),
                ("sku", seen_sku),
            ):
                value = product_row.get(key)
                if value and value in seen_values:
                    duplicate = True
                    break

            if duplicate:
                duplicates_removed += 1
                continue

            for key, seen_values in (
                ("upc", seen_upc),
                ("ean", seen_ean),
                ("gtin", seen_gtin),
                ("sku", seen_sku),
            ):
                value = product_row.get(key)
                if value:
                    seen_values.add(value)

            raw_row = {str(column): _json_safe_value(source_row.get(column)) for column in dataframe.columns}
            product_row["raw_row_json"] = json.dumps(raw_row, ensure_ascii=True, default=str)
            product_row["status"] = "pending_analysis"
            rows.append(product_row)
        except Exception:
            errors += 1

    missing_upc = sum(1 for row in rows if not row.get("upc"))

    return ParsedProductsFile(
        rows=rows,
        total_rows=len(dataframe.index),
        products_detected=len(rows) + duplicates_removed,
        duplicates_removed=duplicates_removed,
        skipped_empty_rows=skipped_empty_rows,
        missing_upc=missing_upc,
        errors=errors,
        column_mapping=column_mapping,
    )


async def parse_products_file(upload_file: UploadFile) -> ParsedProductsFile:
    dataframe = await read_uploaded_file(upload_file)
    return parse_products_dataframe(dataframe)


class ExcelService:
    """Facade kept for callers that prefer service-object style."""

    read_uploaded_file = staticmethod(read_uploaded_file)
    parse_suppliers_file = staticmethod(parse_suppliers_file)
    parse_products_file = staticmethod(parse_products_file)
