from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.profiles import get_active_profile_id, scoped_profile_filter
from app.models.analysis import ProductAnalysis
from app.models.email_campaign import EmailLog
from app.models.product import Product
from app.models.supplier import Supplier


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _scoped_products(db: Session, profile_id: int) -> list[Product]:
    return db.query(Product).filter(scoped_profile_filter(Product, profile_id, db)).all()


def _latest_analyses(db: Session, product_ids: list[int]) -> dict[int, ProductAnalysis]:
    if not product_ids:
        return {}
    analyses = (
        db.query(ProductAnalysis)
        .filter(ProductAnalysis.product_id.in_(product_ids))
        .order_by(ProductAnalysis.product_id.asc(), ProductAnalysis.analyzed_at.desc(), ProductAnalysis.id.desc())
        .all()
    )
    latest = {}
    for analysis in analyses:
        if analysis.product_id not in latest:
            latest[analysis.product_id] = analysis
    return latest


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _average(values: list[Decimal]) -> float | None:
    if not values:
        return None
    return float(sum(values) / Decimal(len(values)))


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> dict[str, Any]:
    products = _scoped_products(db, profile_id)
    latest = _latest_analyses(db, [product.id for product in products])
    recommended = [analysis for analysis in latest.values() if analysis.recommendation_status == "buy"]
    roi_values = [analysis.roi for analysis in latest.values() if analysis.roi is not None]
    score_values = [analysis.final_opportunity_score for analysis in latest.values() if analysis.final_opportunity_score is not None]

    return {
        "total_suppliers": db.query(Supplier).filter(scoped_profile_filter(Supplier, profile_id, db)).count(),
        "valid_emails": db.query(Supplier).filter(scoped_profile_filter(Supplier, profile_id, db), Supplier.is_valid_email.is_(True)).count(),
        "emails_sent": db.query(EmailLog).filter(scoped_profile_filter(EmailLog, profile_id, db), EmailLog.status == "sent").count(),
        "products_uploaded": len(products),
        "products_analyzed": len(latest),
        "products_recommended": len(recommended),
        "average_roi": _average(roi_values),
        "average_opportunity_score": _average(score_values),
    }


@router.get("/top-opportunities")
def top_opportunities(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> list[dict[str, Any]]:
    products = {product.id: product for product in _scoped_products(db, profile_id)}
    latest = _latest_analyses(db, list(products))
    analyses = sorted(
        latest.values(),
        key=lambda analysis: analysis.final_opportunity_score or Decimal("-1"),
        reverse=True,
    )[:limit]
    rows = []
    for analysis in analyses:
        product = products.get(analysis.product_id)
        if product is None:
            continue
        rows.append(
            {
                "product_id": product.id,
                "product_name": product.product_name,
                "supplier_id": product.supplier_id,
                "category": product.category,
                "final_opportunity_score": _float_or_none(analysis.final_opportunity_score),
                "roi": _float_or_none(analysis.roi),
                "margin": _float_or_none(analysis.margin),
                "recommendation_status": analysis.recommendation_status,
            }
        )
    return rows


@router.get("/supplier-performance")
def supplier_performance(
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> list[dict[str, Any]]:
    products = {product.id: product for product in _scoped_products(db, profile_id)}
    latest = _latest_analyses(db, list(products))
    suppliers = {
        supplier.id: supplier
        for supplier in db.query(Supplier).filter(scoped_profile_filter(Supplier, profile_id, db)).all()
    }
    counts: dict[int, int] = {}

    for product_id, analysis in latest.items():
        if analysis.recommendation_status not in {"buy", "review"}:
            continue
        product = products.get(product_id)
        if product is None or product.supplier_id is None:
            continue
        counts[product.supplier_id] = counts.get(product.supplier_id, 0) + 1

    rows = []
    for supplier_id, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        supplier = suppliers.get(supplier_id)
        rows.append(
            {
                "supplier_id": supplier_id,
                "supplier_name": (supplier.supplier_name or supplier.company) if supplier else None,
                "recommended_products": count,
            }
        )
    return rows
