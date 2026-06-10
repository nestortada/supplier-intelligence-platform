from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.profiles import get_active_profile_id
from app.services.export_service import EXCEL_MEDIA_TYPE, ExportService, export_filename_headers


router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("")
def list_exports() -> list[dict]:
    return [
        {"name": "Products", "url": "/exports/products.xlsx"},
        {"name": "Recommended Products", "url": "/exports/recommended-products.xlsx"},
        {"name": "Suppliers", "url": "/exports/suppliers.xlsx"},
        {"name": "Summary Report", "url": "/exports/summary-report.xlsx"},
    ]


@router.get("/products.xlsx")
def export_products(
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> StreamingResponse:
    workbook = ExportService(db, profile_id).export_products()
    return StreamingResponse(
        workbook,
        media_type=EXCEL_MEDIA_TYPE,
        headers=export_filename_headers("products.xlsx"),
    )


@router.get("/recommended-products.xlsx")
def export_recommended_products(
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> StreamingResponse:
    workbook = ExportService(db, profile_id).export_recommended_products()
    return StreamingResponse(
        workbook,
        media_type=EXCEL_MEDIA_TYPE,
        headers=export_filename_headers("recommended-products.xlsx"),
    )


@router.get("/suppliers.xlsx")
def export_suppliers(
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> StreamingResponse:
    workbook = ExportService(db, profile_id).export_suppliers()
    return StreamingResponse(
        workbook,
        media_type=EXCEL_MEDIA_TYPE,
        headers=export_filename_headers("suppliers.xlsx"),
    )


@router.get("/summary-report.xlsx")
def export_summary_report(
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> StreamingResponse:
    workbook = ExportService(db, profile_id).export_summary_report()
    return StreamingResponse(
        workbook,
        media_type=EXCEL_MEDIA_TYPE,
        headers=export_filename_headers("summary-report.xlsx"),
    )
