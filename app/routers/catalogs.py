import json
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.profiles import get_active_profile_id, scoped_profile_filter
from app.core.realtime import publish_realtime_event_sync
from app.models.background_job import BackgroundJob
from app.models.product import Product
from app.models.supplier import Supplier
from app.services.excel_service import SupplierFileError, parse_products_file
from app.utils.validators import clean_text

router = APIRouter(prefix="/catalogs", tags=["catalogs"])


class CatalogUploadResponse(BaseModel):
    success: bool
    job_id: int | None = None
    products_detected: int
    products_created: int
    duplicates: int
    missing_upc: int
    errors: int


def _job_error_items(job: BackgroundJob) -> list[dict[str, Any]]:
    if not job.error_items_json:
        return []
    try:
        parsed = json.loads(job.error_items_json)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _job_event_payload(job: BackgroundJob) -> dict[str, Any]:
    return {
        "job_id": job.id,
        "type": job.type,
        "status": job.status,
        "progress": job.progress,
        "total_items": job.total_items,
        "processed_items": job.processed_items,
        "failed_items": job.failed_items,
        "error_message": job.error_message,
        "error_items": _job_error_items(job),
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


def _record_job_error(job: BackgroundJob, row: dict | None, stage: str, message: str) -> None:
    errors = _job_error_items(job)
    errors.append(
        {
            "product_id": None,
            "product_name": row.get("product_name") if row else None,
            "sku": row.get("sku") if row else None,
            "upc": row.get("upc") if row else None,
            "stage": stage,
            "message": message,
        }
    )
    job.error_items_json = json.dumps(errors[-200:], ensure_ascii=True)


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

    job = BackgroundJob(
        profile_id=profile_id,
        type="catalog_upload",
        status="in_progress",
        progress=0,
        total_items=len(parsed_file.rows),
        processed_items=0,
        failed_items=parsed_file.errors,
        error_message=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    publish_realtime_event_sync("job.created", _job_event_payload(job), profile_id)

    supplier = _resolve_supplier(db, supplier_id, supplier_name, profile_id)
    existing_upcs, existing_eans, existing_gtins, existing_skus = _existing_duplicate_keys(
        db, supplier.id, parsed_file.rows, profile_id
    )

    db_duplicates = 0
    products_created = 0

    for index, row in enumerate(parsed_file.rows, start=1):
        if (
            (row.get("upc") and row["upc"] in existing_upcs)
            or (row.get("ean") and row["ean"] in existing_eans)
            or (row.get("gtin") and row["gtin"] in existing_gtins)
            or (row.get("sku") and row["sku"] in existing_skus)
        ):
            db_duplicates += 1
            job.failed_items += 1
            _record_job_error(job, row, "catalog_upload", "Producto duplicado; no se importo.")
            job.processed_items = index
            job.progress = int((job.processed_items / job.total_items) * 100) if job.total_items else 100
            job.updated_at = datetime.utcnow()
            if index == len(parsed_file.rows) or index % 25 == 0:
                db.commit()
                publish_realtime_event_sync("job.updated", _job_event_payload(job), profile_id)
            continue

        product = Product(**row, supplier_id=supplier.id, profile_id=profile_id)
        db.add(product)
        products_created += 1
        job.processed_items = index
        job.progress = int((job.processed_items / job.total_items) * 100) if job.total_items else 100
        job.updated_at = datetime.utcnow()

        if product.upc:
            existing_upcs.add(product.upc)
        if product.ean:
            existing_eans.add(product.ean)
        if product.gtin:
            existing_gtins.add(product.gtin)
        if product.sku:
            existing_skus.add(product.sku)

        if index == len(parsed_file.rows) or index % 25 == 0:
            db.commit()
            publish_realtime_event_sync("job.updated", _job_event_payload(job), profile_id)

    job.status = "completed" if products_created > 0 or job.failed_items < max(job.total_items, 1) else "failed"
    job.progress = 100
    job.updated_at = datetime.utcnow()
    db.commit()
    publish_realtime_event_sync("job.updated", _job_event_payload(job), profile_id)
    publish_realtime_event_sync("products.updated", {"reason": "catalog_upload_finished", "job_id": job.id}, profile_id)

    return CatalogUploadResponse(
        success=True,
        job_id=job.id,
        products_detected=parsed_file.products_detected,
        products_created=products_created,
        duplicates=parsed_file.duplicates_removed + db_duplicates,
        missing_upc=parsed_file.missing_upc,
        errors=parsed_file.errors,
    )
