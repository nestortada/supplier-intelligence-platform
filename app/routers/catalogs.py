from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.profiles import get_active_profile_id, scoped_profile_filter
from app.models.product import Product
from app.models.supplier import Supplier
from app.services.excel_service import SupplierFileError, parse_products_file
from app.utils.validators import clean_text

router = APIRouter(prefix="/catalogs", tags=["catalogs"])


class CatalogUploadResponse(BaseModel):
    success: bool
    products_detected: int
    products_created: int
    duplicates: int
    missing_upc: int
    errors: int


@router.get("")
def list_catalogs() -> list[dict]:
    return []


def _resolve_supplier(db: Session, supplier_id: int | None, supplier_name: str | None, profile_id: int) -> Supplier:
    if supplier_id is None and not clean_text(supplier_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="supplier_id or supplier_name is required.",
        )

    if supplier_id is not None:
        supplier = db.query(Supplier).filter(scoped_profile_filter(Supplier, profile_id, db), Supplier.id == supplier_id).first()
        if supplier is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
        return supplier

    normalized_name = clean_text(supplier_name)
    if normalized_name is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="supplier_id or supplier_name is required.",
        )

    supplier = (
        db.query(Supplier)
        .filter(
            scoped_profile_filter(Supplier, profile_id, db),
            or_(
                func.lower(Supplier.supplier_name) == normalized_name.lower(),
                func.lower(Supplier.company) == normalized_name.lower(),
            )
        )
        .first()
    )
    if supplier is not None:
        return supplier

    supplier = Supplier(supplier_name=normalized_name, profile_id=profile_id)
    db.add(supplier)
    db.flush()
    return supplier


def _existing_duplicate_keys(
    db: Session,
    supplier_id: int,
    rows: list[dict],
    profile_id: int,
) -> tuple[set[str], set[str], set[str], set[str]]:
    upcs = {row["upc"] for row in rows if row.get("upc")}
    eans = {row["ean"] for row in rows if row.get("ean")}
    gtins = {row["gtin"] for row in rows if row.get("gtin")}
    skus = {row["sku"] for row in rows if row.get("sku")}

    existing_upcs: set[str] = set()
    existing_eans: set[str] = set()
    existing_gtins: set[str] = set()
    existing_skus: set[str] = set()

    filters = []
    if upcs:
        filters.append(Product.upc.in_(upcs))
    if eans:
        filters.append(Product.ean.in_(eans))
    if gtins:
        filters.append(Product.gtin.in_(gtins))
    if skus:
        filters.append((Product.supplier_id == supplier_id) & Product.sku.in_(skus))

    if not filters:
        return existing_upcs, existing_eans, existing_gtins, existing_skus

    for product in db.query(Product).filter(scoped_profile_filter(Product, profile_id, db), or_(*filters)).all():
        if product.upc:
            existing_upcs.add(product.upc)
        if product.ean:
            existing_eans.add(product.ean)
        if product.gtin:
            existing_gtins.add(product.gtin)
        if product.supplier_id == supplier_id and product.sku:
            existing_skus.add(product.sku)

    return existing_upcs, existing_eans, existing_gtins, existing_skus


@router.post("/upload", response_model=CatalogUploadResponse)
async def upload_catalog(
    file: Annotated[UploadFile, File(...)],
    supplier_id: Annotated[int | None, Form()] = None,
    supplier_name: Annotated[str | None, Form()] = None,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> CatalogUploadResponse:
    try:
        parsed_file = await parse_products_file(file)
    except SupplierFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    supplier = _resolve_supplier(db, supplier_id, supplier_name, profile_id)
    existing_upcs, existing_eans, existing_gtins, existing_skus = _existing_duplicate_keys(
        db, supplier.id, parsed_file.rows, profile_id
    )

    db_duplicates = 0
    products_created = 0

    for row in parsed_file.rows:
        if (
            (row.get("upc") and row["upc"] in existing_upcs)
            or (row.get("ean") and row["ean"] in existing_eans)
            or (row.get("gtin") and row["gtin"] in existing_gtins)
            or (row.get("sku") and row["sku"] in existing_skus)
        ):
            db_duplicates += 1
            continue

        product = Product(**row, supplier_id=supplier.id, profile_id=profile_id)
        db.add(product)
        products_created += 1

        if product.upc:
            existing_upcs.add(product.upc)
        if product.ean:
            existing_eans.add(product.ean)
        if product.gtin:
            existing_gtins.add(product.gtin)
        if product.sku:
            existing_skus.add(product.sku)

    db.commit()

    return CatalogUploadResponse(
        success=True,
        products_detected=parsed_file.products_detected,
        products_created=products_created,
        duplicates=parsed_file.duplicates_removed + db_duplicates,
        missing_upc=parsed_file.missing_upc,
        errors=parsed_file.errors,
    )
