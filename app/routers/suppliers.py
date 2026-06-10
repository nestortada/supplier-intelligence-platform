from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.profiles import get_active_profile_id, scoped_profile_filter
from app.models.amazon_data import AmazonProductData
from app.models.analysis import ProductAnalysis
from app.models.email_campaign import EmailCampaign, EmailLog
from app.models.product import Product
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierDatabaseClearResponse, SupplierListResponse, SupplierRead, SupplierUploadResponse
from app.services.excel_service import SupplierFileError, parse_suppliers_file

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.post("/upload", response_model=SupplierUploadResponse)
async def upload_suppliers(
    file: Annotated[UploadFile, File(...)],
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> SupplierUploadResponse:
    try:
        parsed_file = await parse_suppliers_file(file)
    except SupplierFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    emails = [row["email"] for row in parsed_file.rows if row.get("email")]
    existing_emails: set[str] = set()

    if emails:
        existing_emails = {
            email
            for (email,) in db.query(func.lower(Supplier.email))
            .filter(
                scoped_profile_filter(Supplier, profile_id, db),
                Supplier.email.isnot(None),
                func.lower(Supplier.email).in_(emails),
            )
            .all()
        }

    db_duplicates = 0
    suppliers_created = 0

    for row in parsed_file.rows:
        email = row.get("email")
        if email and email in existing_emails:
            db_duplicates += 1
            continue

        supplier = Supplier(**row, profile_id=profile_id)
        db.add(supplier)
        suppliers_created += 1

    db.commit()

    duplicates_removed = parsed_file.duplicates_removed + db_duplicates
    suppliers_skipped = parsed_file.skipped_empty_rows + duplicates_removed

    return SupplierUploadResponse(
        success=True,
        total_rows=parsed_file.total_rows,
        valid_emails=parsed_file.valid_emails,
        invalid_emails=parsed_file.invalid_emails,
        duplicates_removed=duplicates_removed,
        suppliers_created=suppliers_created,
        suppliers_skipped=suppliers_skipped,
    )


@router.get("", response_model=SupplierListResponse)
def list_suppliers(
    search: Annotated[str | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
    city: Annotated[str | None, Query()] = None,
    country: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    has_valid_email: Annotated[bool | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> SupplierListResponse:
    query = db.query(Supplier).filter(scoped_profile_filter(Supplier, profile_id, db))

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Supplier.supplier_name.ilike(search_term),
                Supplier.company.ilike(search_term),
                Supplier.email.ilike(search_term),
                Supplier.website.ilike(search_term),
            )
        )

    if category:
        query = query.filter(Supplier.category.ilike(f"%{category.strip()}%"))
    if city:
        query = query.filter(Supplier.city.ilike(f"%{city.strip()}%"))
    if country:
        query = query.filter(Supplier.country.ilike(f"%{country.strip()}%"))
    if status_filter:
        query = query.filter(Supplier.status == status_filter)
    if has_valid_email is not None:
        query = query.filter(Supplier.is_valid_email.is_(has_valid_email))

    total = query.count()
    items = (
        query.order_by(Supplier.created_at.desc(), Supplier.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return SupplierListResponse(items=items, total=total, page=page, page_size=page_size)


@router.delete("/database", response_model=SupplierDatabaseClearResponse)
def clear_supplier_database(
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> SupplierDatabaseClearResponse:
    products = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db)).all()
    product_ids = [product.id for product in products]
    email_logs_deleted = db.query(EmailLog).filter(scoped_profile_filter(EmailLog, profile_id, db)).delete(synchronize_session=False)
    email_campaigns_deleted = (
        db.query(EmailCampaign).filter(scoped_profile_filter(EmailCampaign, profile_id, db)).delete(synchronize_session=False)
    )
    if product_ids:
        db.query(ProductAnalysis).filter(ProductAnalysis.product_id.in_(product_ids)).delete(synchronize_session=False)
        db.query(AmazonProductData).filter(AmazonProductData.product_id.in_(product_ids)).delete(synchronize_session=False)
    products_deleted = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db)).delete(synchronize_session=False)
    suppliers_deleted = db.query(Supplier).filter(scoped_profile_filter(Supplier, profile_id, db)).delete(synchronize_session=False)
    db.commit()

    return SupplierDatabaseClearResponse(
        success=True,
        suppliers_deleted=suppliers_deleted,
        products_deleted=products_deleted,
        email_logs_deleted=email_logs_deleted,
        email_campaigns_deleted=email_campaigns_deleted,
    )


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> Supplier:
    supplier = db.query(Supplier).filter(scoped_profile_filter(Supplier, profile_id, db), Supplier.id == supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    return supplier


@router.delete("/{supplier_id}")
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> dict[str, bool]:
    supplier = db.query(Supplier).filter(scoped_profile_filter(Supplier, profile_id, db), Supplier.id == supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")

    db.delete(supplier)
    db.commit()
    return {"success": True}
