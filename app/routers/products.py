import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.profiles import get_active_profile_id, scoped_profile_filter
from app.core.runtime_settings import RuntimeSettingsService
from app.models.analysis import ProductAnalysis
from app.models.amazon_data import AmazonProductData
from app.models.background_job import BackgroundJob
from app.models.product import Product
from app.schemas.product import (
    AnalyzeProductsRequest,
    AnalyzeProductsResponse,
    BulkUpdateStatusRequest,
    BulkUpdateStatusResponse,
    EnrichApifyRequest,
    EnrichApifyResponse,
    ProductDatabaseClearResponse,
    ProductListResponse,
    ProductPerformanceUpdateRequest,
    ProductRead,
    ProductSelectionClearResponse,
    ProductSelectionResponse,
    ProductSelectionUpdateRequest,
)
from app.services.apify_service import ApifyService, map_apify_item_to_amazon_data
from app.services.product_scoring_engine import ProductScoringEngine
from app.services.sync_service import enqueue_delete_tombstones
from app.core.realtime import publish_realtime_event_sync


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])
RECENT_AMAZON_DATA_DAYS = 30


def _scoring_engine_from_settings() -> ProductScoringEngine:
    runtime_settings = RuntimeSettingsService()
    fees = runtime_settings.get_fees()
    return ProductScoringEngine(
        referral_fee_rate=fees["referral_fee_rate"],
        fba_fee=fees["default_fba_fee"],
        shipping_cost=fees["default_shipping_cost"],
        prep_fee=fees["default_prep_fee"],
        other_costs=fees["default_other_costs"],
        weights=runtime_settings.get_scoring(),
    )


def get_apify_service() -> ApifyService:
    return ApifyService()


def _latest_recent_amazon_data(db: Session, product_id: int) -> AmazonProductData | None:
    cutoff = datetime.utcnow() - timedelta(days=RECENT_AMAZON_DATA_DAYS)
    return (
        db.query(AmazonProductData)
        .filter(AmazonProductData.product_id == product_id, AmazonProductData.captured_at >= cutoff)
        .order_by(AmazonProductData.captured_at.desc(), AmazonProductData.id.desc())
        .first()
    )


def _latest_amazon_data(db: Session, product_id: int) -> AmazonProductData | None:
    return (
        db.query(AmazonProductData)
        .filter(AmazonProductData.product_id == product_id)
        .order_by(AmazonProductData.captured_at.desc(), AmazonProductData.id.desc())
        .first()
    )


def _latest_product_analysis(db: Session, product_id: int) -> ProductAnalysis | None:
    return (
        db.query(ProductAnalysis)
        .filter(ProductAnalysis.product_id == product_id)
        .order_by(ProductAnalysis.analyzed_at.desc(), ProductAnalysis.id.desc())
        .first()
    )


def _update_job_progress(db: Session, job: BackgroundJob) -> None:
    job.progress = int((job.processed_items / job.total_items) * 100) if job.total_items else 100
    job.updated_at = datetime.utcnow()
    db.commit()
    publish_realtime_event_sync("job.updated", _job_event_payload(job), job.profile_id)


def _job_error_items(job: BackgroundJob) -> list[dict[str, Any]]:
    if not job.error_items_json:
        return []
    try:
        parsed = json.loads(job.error_items_json)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _record_job_error(job: BackgroundJob, product: Product | None, stage: str, message: str) -> None:
    errors = _job_error_items(job)
    errors.append(
        {
            "product_id": product.id if product else None,
            "product_name": product.product_name if product else None,
            "sku": product.sku if product else None,
            "upc": product.upc if product else None,
            "stage": stage,
            "message": message,
        }
    )
    job.error_items_json = json.dumps(errors[-200:], ensure_ascii=True)


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


def _decimal_field(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _float_field(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _json_value(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _json_list(value: str | None) -> list:
    parsed = _json_value(value)
    return parsed if isinstance(parsed, list) else []


def _product_payload(product: Product) -> dict[str, Any]:
    return {
        "id": product.id,
        "supplier_id": product.supplier_id,
        "product_name": product.product_name,
        "description": product.description,
        "sku": product.sku,
        "upc": product.upc,
        "ean": product.ean,
        "gtin": product.gtin,
        "brand": product.brand,
        "category": product.category,
        "supplier_cost": _float_field(product.supplier_cost),
        "case_quantity": product.case_quantity,
        "uom": product.uom,
        "status": product.status,
        "selected_for_sale": product.selected_for_sale,
        "sale_performance": product.sale_performance,
        "selected_at": product.selected_at,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }


def _amazon_data_payload(amazon_data: AmazonProductData | None) -> dict[str, Any] | None:
    if amazon_data is None:
        return None

    return {
        "id": amazon_data.id,
        "product_id": amazon_data.product_id,
        "asin": amazon_data.asin,
        "amazon_title": amazon_data.amazon_title,
        "amazon_url": amazon_data.amazon_url,
        "image_url": amazon_data.image_url,
        "current_price": _float_field(amazon_data.current_price),
        "buybox_price": _float_field(amazon_data.buybox_price),
        "amazon_price": _float_field(amazon_data.amazon_price),
        "list_price": _float_field(amazon_data.list_price),
        "currency": amazon_data.currency,
        "rating": _float_field(amazon_data.rating),
        "reviews_count": amazon_data.reviews_count,
        "sellers_count": amazon_data.sellers_count,
        "estimated_sales": amazon_data.estimated_sales,
        "price_history_json": amazon_data.price_history_json,
        "sellers_history_json": amazon_data.sellers_history_json,
        "captured_at": amazon_data.captured_at,
    }


def _scores_payload(analysis: ProductAnalysis) -> dict[str, float | None]:
    return {
        "profitability_score": _float_field(analysis.profitability_score),
        "roi_score": _float_field(analysis.roi_score),
        "sales_score": _float_field(analysis.sales_score),
        "price_stability_score": _float_field(analysis.price_stability_score),
        "sellers_score": _float_field(analysis.sellers_score),
        "data_quality_score": _float_field(analysis.data_quality_score),
        "final_opportunity_score": _float_field(analysis.final_opportunity_score),
    }


def _analysis_payload(analysis: ProductAnalysis) -> dict[str, Any]:
    return {
        "id": analysis.id,
        "product_id": analysis.product_id,
        "net_profit": _float_field(analysis.net_profit),
        "margin": _float_field(analysis.margin),
        "roi": _float_field(analysis.roi),
        **_scores_payload(analysis),
        "recommendation_status": analysis.recommendation_status,
        "recommendation_reason": analysis.recommendation_reason,
        "risks": _json_list(analysis.risks_json),
        "analyzed_at": analysis.analyzed_at,
    }


def _selected_product_payload(db: Session, product: Product) -> dict[str, Any]:
    analysis = _latest_product_analysis(db, product.id)
    amazon_data = _latest_amazon_data(db, product.id)
    return {
        "product": _product_payload(product),
        "amazon_data": _amazon_data_payload(amazon_data),
        "analysis": _analysis_payload(analysis) if analysis else None,
        "scores": _scores_payload(analysis) if analysis else None,
        "recommendation": {
            "status": analysis.recommendation_status if analysis else product.status,
            "reason": analysis.recommendation_reason if analysis else None,
            "risks": _json_list(analysis.risks_json) if analysis else [],
        },
        "sale_performance": product.sale_performance,
        "selected_at": product.selected_at,
    }


def _analysis_from_result(product_id: int, result: dict[str, Any]) -> ProductAnalysis:
    return ProductAnalysis(
        product_id=product_id,
        net_profit=_decimal_field(result["net_profit"]),
        margin=_decimal_field(result["margin"]),
        roi=_decimal_field(result["roi"]),
        profitability_score=_decimal_field(result["profitability_score"]),
        roi_score=_decimal_field(result["roi_score"]),
        sales_score=_decimal_field(result["sales_score"]),
        price_stability_score=_decimal_field(result["price_stability_score"]),
        sellers_score=_decimal_field(result["sellers_score"]),
        data_quality_score=_decimal_field(result["data_quality_score"]),
        final_opportunity_score=_decimal_field(result["final_opportunity_score"]),
        recommendation_status=result["recommendation_status"],
        recommendation_reason=result["recommendation_reason"],
        risks_json=json.dumps(result["risks"], ensure_ascii=True),
    )


def run_apify_enrichment(
    job_id: int,
    product_ids: list[int],
    profile_id: int,
    force_refresh: bool = False,
    run_analysis_after: bool = False,
    apify_service: ApifyService | None = None,
) -> None:
    db = SessionLocal()
    service = apify_service or ApifyService()

    try:
        job = db.query(BackgroundJob).filter(scoped_profile_filter(BackgroundJob, profile_id, db), BackgroundJob.id == job_id).first()
        if job is None:
            logger.error("apify_job_missing", extra={"job_id": job_id})
            return

        job.status = "in_progress"
        job.total_items = len(product_ids)
        job.progress = 0 if product_ids else 100
        db.commit()
        publish_realtime_event_sync("job.updated", _job_event_payload(job), profile_id)

        for product_id in product_ids:
            db.expire_all()
            job = db.query(BackgroundJob).filter(scoped_profile_filter(BackgroundJob, profile_id, db), BackgroundJob.id == job_id).first()
            if job is None:
                logger.error("apify_job_missing_during_loop", extra={"job_id": job_id})
                return
            if job.status == "canceled":
                job.progress = 100
                job.updated_at = datetime.utcnow()
                db.commit()
                return

            product = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db), Product.id == product_id).first()
            if product is None:
                job.failed_items += 1
                _record_job_error(job, None, "apify", f"Producto {product_id} no existe o no pertenece al perfil.")
                job.processed_items += 1
                _update_job_progress(db, job)
                continue

            try:
                if not force_refresh and _latest_recent_amazon_data(db, product.id):
                    job.processed_items += 1
                    _update_job_progress(db, job)
                    continue

                item = service.search_amazon_product(product)
                if item:
                    db.add(map_apify_item_to_amazon_data(product.id, item))
                    product.status = "enriched"
                else:
                    product.status = "insufficient_data"
                    job.failed_items += 1
                    _record_job_error(job, product, "apify", "Apify no devolvio datos suficientes para este producto.")

                product.updated_at = datetime.utcnow()
            except Exception as exc:
                logger.exception("apify_product_enrichment_failed", extra={"job_id": job_id, "product_id": product.id})
                job.failed_items += 1
                job.error_message = str(exc)
                _record_job_error(job, product, "apify", str(exc))

            job.processed_items += 1
            _update_job_progress(db, job)

        if job.total_items == 0:
            job.status = "completed"
        elif job.failed_items >= job.total_items:
            job.status = "failed"
        else:
            job.status = "completed"

        job.progress = 100
        job.updated_at = datetime.utcnow()
        db.commit()
        publish_realtime_event_sync("job.updated", _job_event_payload(job), profile_id)
        publish_realtime_event_sync("products.updated", {"reason": "apify_enrichment_finished", "job_id": job.id}, profile_id)

        if job.status == "completed" and run_analysis_after:
            analysis_products = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db)).order_by(Product.id.asc()).all()
            analysis_job = BackgroundJob(
                profile_id=profile_id,
                type="product_analysis",
                status="in_progress" if analysis_products else "completed",
                progress=0 if analysis_products else 100,
                total_items=len(analysis_products),
                processed_items=0,
                failed_items=0,
            )
            db.add(analysis_job)
            db.commit()
            db.refresh(analysis_job)
            publish_realtime_event_sync("job.created", _job_event_payload(analysis_job), profile_id)
            if analysis_products:
                run_product_analysis(analysis_job.id, [product.id for product in analysis_products], profile_id)
    except Exception as exc:
        logger.exception("apify_job_failed", extra={"job_id": job_id})
        job = db.query(BackgroundJob).filter(scoped_profile_filter(BackgroundJob, profile_id, db), BackgroundJob.id == job_id).first()
        if job is not None:
            job.status = "failed"
            job.error_message = str(exc)
            job.updated_at = datetime.utcnow()
            db.commit()
            publish_realtime_event_sync("job.updated", _job_event_payload(job), profile_id)
    finally:
        db.close()


def run_product_analysis(job_id: int, product_ids: list[int], profile_id: int) -> None:
    db = SessionLocal()
    engine = _scoring_engine_from_settings()

    try:
        job = db.query(BackgroundJob).filter(scoped_profile_filter(BackgroundJob, profile_id, db), BackgroundJob.id == job_id).first()
        if job is None:
            logger.error("product_analysis_job_missing", extra={"job_id": job_id})
            return

        job.status = "in_progress"
        job.total_items = len(product_ids)
        job.progress = 0 if product_ids else 100
        db.commit()
        publish_realtime_event_sync("job.updated", _job_event_payload(job), profile_id)

        for product_id in product_ids:
            db.expire_all()
            job = db.query(BackgroundJob).filter(scoped_profile_filter(BackgroundJob, profile_id, db), BackgroundJob.id == job_id).first()
            if job is None:
                logger.error("product_analysis_job_missing_during_loop", extra={"job_id": job_id})
                return
            if job.status == "canceled":
                job.progress = 100
                job.updated_at = datetime.utcnow()
                db.commit()
                return

            product = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db), Product.id == product_id).first()
            if product is None:
                job.failed_items += 1
                _record_job_error(job, None, "analysis", f"Producto {product_id} no existe o no pertenece al perfil.")
                job.processed_items += 1
                _update_job_progress(db, job)
                continue

            try:
                amazon_data = _latest_amazon_data(db, product.id)
                result = engine.analyze_product(product, amazon_data)
                db.add(_analysis_from_result(product.id, result))
                product.status = result["recommendation_status"]
                product.updated_at = datetime.utcnow()
            except Exception as exc:
                logger.exception("product_analysis_failed", extra={"job_id": job_id, "product_id": product.id})
                job.failed_items += 1
                job.error_message = str(exc)
                _record_job_error(job, product, "analysis", str(exc))

            job.processed_items += 1
            _update_job_progress(db, job)

        if job.total_items == 0:
            job.status = "completed"
        elif job.failed_items >= job.total_items:
            job.status = "failed"
        else:
            job.status = "completed"

        job.progress = 100
        job.updated_at = datetime.utcnow()
        db.commit()
        publish_realtime_event_sync("job.updated", _job_event_payload(job), profile_id)
        publish_realtime_event_sync("products.updated", {"reason": "product_analysis_finished", "job_id": job.id}, profile_id)
    except Exception as exc:
        logger.exception("product_analysis_job_failed", extra={"job_id": job_id})
        job = db.query(BackgroundJob).filter(scoped_profile_filter(BackgroundJob, profile_id, db), BackgroundJob.id == job_id).first()
        if job is not None:
            job.status = "failed"
            job.error_message = str(exc)
            job.updated_at = datetime.utcnow()
            db.commit()
            publish_realtime_event_sync("job.updated", _job_event_payload(job), profile_id)
    finally:
        db.close()


@router.post("/analyze", response_model=AnalyzeProductsResponse)
def analyze_products(
    payload: AnalyzeProductsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> AnalyzeProductsResponse:
    has_product_ids = bool(payload.product_ids)
    if has_product_ids == payload.all:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either product_ids or all=true.",
        )

    if payload.all:
        products = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db)).order_by(Product.id.asc()).all()
    else:
        products = (
            db.query(Product)
            .filter(scoped_profile_filter(Product, profile_id, db), Product.id.in_(payload.product_ids or []))
            .order_by(Product.id.asc())
            .all()
        )

    if not products and has_product_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No products found.")

    job = BackgroundJob(
        profile_id=profile_id,
        type="product_analysis",
        status="in_progress" if products else "completed",
        progress=0 if products else 100,
        total_items=len(products),
        processed_items=0,
        failed_items=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    publish_realtime_event_sync("job.created", _job_event_payload(job), profile_id)

    if products:
        background_tasks.add_task(run_product_analysis, job.id, [product.id for product in products], profile_id)

    return AnalyzeProductsResponse(success=True, job_id=job.id, total_items=job.total_items, status=job.status)


@router.get("/ranking")
def list_product_ranking(
    min_score: Annotated[Decimal | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    supplier_id: Annotated[int | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
    min_roi: Annotated[Decimal | None, Query()] = None,
    min_margin: Annotated[Decimal | None, Query()] = None,
    min_sales: Annotated[int | None, Query()] = None,
    sellers_min: Annotated[int | None, Query()] = None,
    sellers_max: Annotated[int | None, Query()] = None,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> list[dict]:
    scoped_products = {product.id: product for product in db.query(Product).filter(scoped_profile_filter(Product, profile_id, db)).all()}
    if not scoped_products:
        return []
    analyses = (
        db.query(ProductAnalysis)
        .filter(ProductAnalysis.product_id.in_(list(scoped_products)))
        .order_by(ProductAnalysis.product_id.asc(), ProductAnalysis.analyzed_at.desc(), ProductAnalysis.id.desc())
        .all()
    )
    latest_by_product_id: dict[int, ProductAnalysis] = {}
    for analysis in analyses:
        if analysis.product_id not in latest_by_product_id:
            latest_by_product_id[analysis.product_id] = analysis

    ranking = []
    for analysis in latest_by_product_id.values():
        product = scoped_products.get(analysis.product_id)
        if product is None:
            continue
        amazon_data = _latest_amazon_data(db, product.id)

        if min_score is not None and (analysis.final_opportunity_score is None or analysis.final_opportunity_score < min_score):
            continue
        if status_filter and analysis.recommendation_status != status_filter:
            continue
        if supplier_id is not None and product.supplier_id != supplier_id:
            continue
        if category and (not product.category or category.strip().lower() not in product.category.lower()):
            continue
        if min_roi is not None and (analysis.roi is None or analysis.roi < min_roi):
            continue
        if min_margin is not None and (analysis.margin is None or analysis.margin < min_margin):
            continue
        if min_sales is not None and (amazon_data is None or amazon_data.estimated_sales is None or amazon_data.estimated_sales < min_sales):
            continue
        if sellers_min is not None and (amazon_data is None or amazon_data.sellers_count is None or amazon_data.sellers_count < sellers_min):
            continue
        if sellers_max is not None and (amazon_data is None or amazon_data.sellers_count is None or amazon_data.sellers_count > sellers_max):
            continue

        ranking.append(
            {
                "product": _product_payload(product),
                "amazon_data": _amazon_data_payload(amazon_data),
                "analysis": _analysis_payload(analysis),
                "scores": _scores_payload(analysis),
                "recommendation": {
                    "status": analysis.recommendation_status,
                    "reason": analysis.recommendation_reason,
                    "risks": _json_list(analysis.risks_json),
                },
            }
        )

    ranking.sort(key=lambda item: item["scores"]["final_opportunity_score"] or 0, reverse=True)
    return ranking


@router.get("", response_model=ProductListResponse)
def list_products(
    supplier_id: Annotated[int | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
    brand: Annotated[str | None, Query()] = None,
    has_upc: Annotated[bool | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    min_cost: Annotated[Decimal | None, Query()] = None,
    max_cost: Annotated[Decimal | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> ProductListResponse:
    query = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db))

    if supplier_id is not None:
        query = query.filter(Product.supplier_id == supplier_id)
    if category:
        query = query.filter(Product.category.ilike(f"%{category.strip()}%"))
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand.strip()}%"))
    if has_upc is True:
        query = query.filter(Product.upc.isnot(None), Product.upc != "")
    elif has_upc is False:
        query = query.filter(or_(Product.upc.is_(None), Product.upc == ""))
    if status_filter:
        query = query.filter(Product.status == status_filter)
    if min_cost is not None:
        query = query.filter(Product.supplier_cost >= min_cost)
    if max_cost is not None:
        query = query.filter(Product.supplier_cost <= max_cost)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Product.product_name.ilike(search_term),
                Product.description.ilike(search_term),
                Product.sku.ilike(search_term),
                Product.upc.ilike(search_term),
                Product.ean.ilike(search_term),
                Product.gtin.ilike(search_term),
                Product.brand.ilike(search_term),
                Product.category.ilike(search_term),
            )
        )

    total = query.count()
    items = (
        query.order_by(Product.created_at.desc(), Product.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ProductListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/selected")
def list_selected_products(
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> list[dict[str, Any]]:
    products = (
        db.query(Product)
        .filter(scoped_profile_filter(Product, profile_id, db), Product.selected_for_sale.is_(True))
        .order_by(Product.selected_at.desc(), Product.updated_at.desc(), Product.id.desc())
        .all()
    )
    return [_selected_product_payload(db, product) for product in products]


@router.patch("/selected/performance", response_model=ProductSelectionResponse)
def update_selected_product_performance(
    request: ProductPerformanceUpdateRequest,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> ProductSelectionResponse:
    product = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db), Product.id == request.product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    if not product.selected_for_sale:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product is not selected.")

    product.sale_performance = request.sale_performance
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)
    publish_realtime_event_sync(
        "product.selection_updated",
        {
            "product_id": product.id,
            "selected_for_sale": product.selected_for_sale,
            "sale_performance": product.sale_performance,
            "selected_at": product.selected_at.isoformat() if product.selected_at else None,
        },
        profile_id,
    )
    return ProductSelectionResponse(success=True, product=product)


@router.delete("/selected", response_model=ProductSelectionClearResponse)
def clear_selected_products(
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> ProductSelectionClearResponse:
    products = (
        db.query(Product)
        .filter(scoped_profile_filter(Product, profile_id, db), Product.selected_for_sale.is_(True))
        .all()
    )
    now = datetime.utcnow()
    for product in products:
        product.selected_for_sale = False
        product.sale_performance = None
        product.selected_at = None
        product.updated_at = now

    db.commit()
    publish_realtime_event_sync("products.selection_cleared", {"updated": len(products)}, profile_id)
    return ProductSelectionClearResponse(success=True, updated=len(products))


@router.patch("/{product_id}/selection", response_model=ProductSelectionResponse)
def update_product_selection(
    product_id: int,
    request: ProductSelectionUpdateRequest,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> ProductSelectionResponse:
    product = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db), Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    now = datetime.utcnow()
    if request.selected_for_sale:
        if not product.selected_for_sale:
            product.selected_at = now
        product.selected_for_sale = True
        product.sale_performance = request.sale_performance
    else:
        product.selected_for_sale = False
        product.sale_performance = None
        product.selected_at = None

    product.updated_at = now
    db.commit()
    db.refresh(product)
    publish_realtime_event_sync(
        "product.selection_updated",
        {
            "product_id": product.id,
            "selected_for_sale": product.selected_for_sale,
            "sale_performance": product.sale_performance,
            "selected_at": product.selected_at.isoformat() if product.selected_at else None,
        },
        profile_id,
    )
    return ProductSelectionResponse(success=True, product=product)


@router.post("/bulk-update-status", response_model=BulkUpdateStatusResponse)
def bulk_update_status(
    request: BulkUpdateStatusRequest,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> BulkUpdateStatusResponse:
    if not request.product_ids:
        return BulkUpdateStatusResponse(success=True, updated=0)

    products = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db), Product.id.in_(request.product_ids)).all()
    for product in products:
        product.status = request.status

    db.commit()
    publish_realtime_event_sync("products.updated", {"reason": "bulk_status", "updated": len(products), "status": request.status}, profile_id)
    return BulkUpdateStatusResponse(success=True, updated=len(products))


@router.post("/enrich-apify", response_model=EnrichApifyResponse)
def enrich_products_with_apify(
    payload: EnrichApifyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
    apify_service: ApifyService = Depends(get_apify_service),
) -> EnrichApifyResponse:
    has_product_ids = bool(payload.product_ids)
    if has_product_ids == payload.all_pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either product_ids or all_pending=true.",
        )

    if payload.all_pending:
        products = (
            db.query(Product)
            .filter(scoped_profile_filter(Product, profile_id, db), Product.status == "pending_analysis")
            .order_by(Product.id.asc())
            .all()
        )
    else:
        products = (
            db.query(Product)
            .filter(scoped_profile_filter(Product, profile_id, db), Product.id.in_(payload.product_ids or []))
            .order_by(Product.id.asc())
            .all()
        )

    if not products and has_product_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No products found.")

    job = BackgroundJob(
        profile_id=profile_id,
        type="apify_enrichment",
        status="in_progress" if products else "completed",
        progress=0 if products else 100,
        total_items=len(products),
        processed_items=0,
        failed_items=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    publish_realtime_event_sync("job.created", _job_event_payload(job), profile_id)

    if products:
        background_tasks.add_task(
            run_apify_enrichment,
            job.id,
            [product.id for product in products],
            profile_id,
            payload.force_refresh,
            payload.run_analysis_after,
            apify_service,
        )

    return EnrichApifyResponse(success=True, job_id=job.id, total_items=job.total_items, status=job.status)


@router.get("/{product_id}/analysis")
def get_product_analysis(
    product_id: int,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> dict[str, Any]:
    product = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db), Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    analysis = _latest_product_analysis(db, product_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product analysis not found.")

    amazon_data = _latest_amazon_data(db, product_id)
    recalculated = _scoring_engine_from_settings().analyze_product(product, amazon_data)

    return {
        "product": _product_payload(product),
        "amazon_data": _amazon_data_payload(amazon_data),
        "financial_analysis": {
            "supplier_cost": recalculated["supplier_cost"],
            "amazon_price": recalculated["amazon_price"],
            "referral_fee": recalculated["referral_fee"],
            "fba_fee": recalculated["fba_fee"],
            "shipping_cost": recalculated["shipping_cost"],
            "prep_fee": recalculated["prep_fee"],
            "other_costs": recalculated["other_costs"],
            "total_cost": recalculated["total_cost"],
            "net_profit": _float_field(analysis.net_profit),
            "margin": _float_field(analysis.margin),
            "roi": _float_field(analysis.roi),
        },
        "scores": _scores_payload(analysis),
        "recommendation": {
            "status": analysis.recommendation_status,
            "reason": analysis.recommendation_reason,
            "risks": _json_list(analysis.risks_json),
        },
        "risks": _json_list(analysis.risks_json),
        "price_history": recalculated["price_history"],
        "price_history_metrics": recalculated["price_history_metrics"],
        "sellers_history": _json_value(amazon_data.sellers_history_json) if amazon_data else None,
    }


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> Product:
    product = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db), Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


@router.delete("/database", response_model=ProductDatabaseClearResponse)
def clear_product_database(
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> ProductDatabaseClearResponse:
    products = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db)).all()
    product_ids = [
        product.id
        for product in products
    ]
    analyses_deleted = 0
    amazon_data_deleted = 0
    if product_ids:
        analyses = db.query(ProductAnalysis).filter(ProductAnalysis.product_id.in_(product_ids)).all()
        amazon_rows = db.query(AmazonProductData).filter(AmazonProductData.product_id.in_(product_ids)).all()
        enqueue_delete_tombstones(db, [*analyses, *amazon_rows, *products])
        analyses_deleted = db.query(ProductAnalysis).filter(ProductAnalysis.product_id.in_(product_ids)).delete(synchronize_session=False)
        amazon_data_deleted = db.query(AmazonProductData).filter(AmazonProductData.product_id.in_(product_ids)).delete(synchronize_session=False)
    products_deleted = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db)).delete(synchronize_session=False)
    db.commit()
    publish_realtime_event_sync(
        "products.deleted",
        {
            "products_deleted": products_deleted,
            "amazon_data_deleted": amazon_data_deleted,
            "analyses_deleted": analyses_deleted,
        },
        profile_id,
    )

    return ProductDatabaseClearResponse(
        success=True,
        products_deleted=products_deleted,
        amazon_data_deleted=amazon_data_deleted,
        analyses_deleted=analyses_deleted,
    )


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> dict[str, bool]:
    product = db.query(Product).filter(scoped_profile_filter(Product, profile_id, db), Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    db.delete(product)
    db.commit()
    publish_realtime_event_sync("product.deleted", {"product_id": product_id}, profile_id)
    return {"success": True}
