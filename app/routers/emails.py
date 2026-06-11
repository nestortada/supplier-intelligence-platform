import logging
import time
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.core.profiles import get_active_profile_id, scoped_profile_filter
from app.core.realtime import publish_realtime_event_sync
from app.models.email_campaign import EmailCampaign, EmailLog
from app.models.supplier import Supplier
from app.schemas.email import (
    CampaignListResponse,
    CampaignSummary,
    CampaignStatusResponse,
    CreateEmailCampaignRequest,
    EmailLogRead,
    EmailSendResponse,
    SendEmailRequest,
)
from app.schemas.supplier import SupplierListResponse
from app.services.emailjs_service import EmailJSService
from app.utils.validators import is_valid_email, normalize_email


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emails", tags=["emails"])

DEFAULT_EMAIL_SUBJECT = "Request for Product Catalog and Wholesale Pricing"
TEMPLATE_ID_PLACEHOLDERS = {"", "string", "optional_template_id", "optional", "null", "none"}
DEFAULT_EMAIL_MESSAGE = (
    "Hello {supplier_name},\n\n"
    "My name is {my_name}.\n\n"
    "I am currently researching products and suppliers across different categories and came across your company "
    "during my search.\n\n"
    "I would be interested in learning more about your product offerings and reviewing your latest catalog.\n\n"
    "If possible, could you please share:\n\n"
    "Your latest product catalog (Excel, CSV, PDF, or website link)\n"
    "Current wholesale pricing\n"
    "UPC, EAN, GTIN, SKU, or product identifiers (if available)\n"
    "Minimum Order Quantities (MOQ)\n"
    "Shipping and lead times\n"
    "Payment terms\n"
    "Volume discount opportunities\n\n"
    "I am currently evaluating products and suppliers for potential purchasing opportunities and would appreciate "
    "any information you can provide.\n\n"
    "Thank you for your time and consideration. I look forward to hearing from you.\n\n\n"
    "Best regards,\n\n"
    "{my_name}\n"
    "Email: {my_email}\n"
    "Phone: {my_phone}"
)


def get_email_service() -> EmailJSService:
    return EmailJSService()


def normalize_template_id(template_id: str | None) -> str | None:
    if template_id is None:
        return None

    normalized = template_id.strip()
    if normalized.lower() in TEMPLATE_ID_PLACEHOLDERS:
        return None

    return normalized


def build_template_params(supplier: Supplier, subject: str, template_id: str | None = None) -> dict[str, str | None]:
    supplier_name = supplier.supplier_name or supplier.company or "there"
    message = DEFAULT_EMAIL_MESSAGE.format(
        supplier_name=supplier_name,
        my_name=settings.MY_NAME,
        my_email=settings.MY_EMAIL,
        my_phone=settings.MY_PHONE,
    )
    params = {
        "to_email": supplier.email,
        "email": supplier.email,
        "supplier_name": supplier_name,
        "company": supplier.company,
        "category": supplier.category,
        "city": supplier.city,
        "website": supplier.website,
        "my_name": settings.MY_NAME,
        "my_email": settings.MY_EMAIL,
        "my_phone": settings.MY_PHONE,
        "subject": subject,
        "message": message,
        "menssage": message,
        "g-recaptcha-response": "",
    }
    normalized_template_id = normalize_template_id(template_id)
    if normalized_template_id:
        params["_template_id"] = normalized_template_id
    return params


def is_supplier_sendable(supplier: Supplier) -> bool:
    return bool(supplier.email and supplier.is_valid_email and is_valid_email(supplier.email))


def dedupe_sendable_suppliers(suppliers: list[Supplier]) -> list[Supplier]:
    deduped: list[Supplier] = []
    seen_emails: set[str] = set()

    for supplier in suppliers:
        if not is_supplier_sendable(supplier):
            continue

        email = normalize_email(supplier.email)
        if not email or email in seen_emails:
            continue

        seen_emails.add(email)
        deduped.append(supplier)

    return deduped


def send_supplier_email(
    db: Session,
    supplier: Supplier,
    subject: str,
    template_id: str | None,
    email_service: EmailJSService,
    campaign_id: int | None = None,
    profile_id: int | None = None,
) -> EmailLog:
    template_params = build_template_params(supplier, subject, template_id)
    result = email_service.send_email(supplier.email or "", template_params)
    now = datetime.utcnow()

    log = EmailLog(
        profile_id=profile_id if profile_id is not None else supplier.profile_id,
        campaign_id=campaign_id,
        supplier_id=supplier.id,
        to_email=supplier.email,
        status="sent" if result["success"] else "failed",
        provider_response=result.get("response"),
        error_message=result.get("error"),
        sent_at=now if result["success"] else None,
    )
    db.add(log)

    supplier.status = "email_sent" if result["success"] else "error"
    supplier.updated_at = now
    db.commit()
    db.refresh(log)
    publish_realtime_event_sync(
        "email.sent",
        {
            "log_id": log.id,
            "campaign_id": campaign_id,
            "supplier_id": supplier.id,
            "status": log.status,
            "to_email": log.to_email,
        },
        log.profile_id,
    )

    return log


def run_campaign(campaign_id: int, supplier_ids: list[int], subject: str, template_id: str | None, profile_id: int) -> None:
    db = SessionLocal()
    email_service = EmailJSService()

    try:
        campaign = db.query(EmailCampaign).filter(scoped_profile_filter(EmailCampaign, profile_id, db), EmailCampaign.id == campaign_id).first()
        if campaign is None:
            logger.error("email_campaign_missing", extra={"campaign_id": campaign_id})
            return

        for index, supplier_id in enumerate(supplier_ids):
            db.expire_all()
            campaign = db.query(EmailCampaign).filter(scoped_profile_filter(EmailCampaign, profile_id, db), EmailCampaign.id == campaign_id).first()
            if campaign is None:
                return
            if campaign.status == "canceled":
                campaign.updated_at = datetime.utcnow()
                db.commit()
                return

            supplier = db.query(Supplier).filter(scoped_profile_filter(Supplier, profile_id, db), Supplier.id == supplier_id).first()
            if supplier is None or not is_supplier_sendable(supplier):
                continue

            log = send_supplier_email(db, supplier, subject, template_id, email_service, campaign_id=campaign_id, profile_id=profile_id)

            campaign = db.query(EmailCampaign).filter(scoped_profile_filter(EmailCampaign, profile_id, db), EmailCampaign.id == campaign_id).first()
            if campaign is None:
                return

            if log.status == "sent":
                campaign.sent_count += 1
            else:
                campaign.failed_count += 1

            campaign.updated_at = datetime.utcnow()
            db.commit()
            publish_realtime_event_sync("email_campaign.updated", campaign_event_payload(campaign), profile_id)

            if index < len(supplier_ids) - 1:
                time.sleep(1)

        campaign = db.query(EmailCampaign).filter(scoped_profile_filter(EmailCampaign, profile_id, db), EmailCampaign.id == campaign_id).first()
        if campaign is None:
            return

        if campaign.total_recipients == 0:
            campaign.status = "completed"
        elif campaign.sent_count == 0 and campaign.failed_count >= campaign.total_recipients:
            campaign.status = "failed"
        else:
            campaign.status = "completed"

        campaign.updated_at = datetime.utcnow()
        db.commit()
        publish_realtime_event_sync("email_campaign.updated", campaign_event_payload(campaign), profile_id)
    except Exception:
        logger.exception("email_campaign_unexpected_error", extra={"campaign_id": campaign_id})
        campaign = db.query(EmailCampaign).filter(scoped_profile_filter(EmailCampaign, profile_id, db), EmailCampaign.id == campaign_id).first()
        if campaign is not None:
            campaign.status = "error"
            campaign.updated_at = datetime.utcnow()
            db.commit()
            publish_realtime_event_sync("email_campaign.updated", campaign_event_payload(campaign), profile_id)
    finally:
        db.close()


def create_campaign(
    db: Session,
    suppliers: list[Supplier],
    subject: str,
    template_id: str | None,
    profile_id: int,
) -> tuple[EmailCampaign, list[int]]:
    deduped_suppliers = dedupe_sendable_suppliers(suppliers)
    campaign = EmailCampaign(
        profile_id=profile_id,
        subject=subject,
        template_id=template_id or settings.EMAILJS_TEMPLATE_ID,
        status="in_progress" if deduped_suppliers else "completed",
        total_recipients=len(deduped_suppliers),
        sent_count=0,
        failed_count=0,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    publish_realtime_event_sync("email_campaign.created", campaign_event_payload(campaign), profile_id)

    return campaign, [supplier.id for supplier in deduped_suppliers]


def campaign_status_response(campaign: EmailCampaign) -> CampaignStatusResponse:
    return CampaignStatusResponse(
        campaign_id=campaign.id,
        status=campaign.status,
        total=campaign.total_recipients,
        sent=campaign.sent_count,
        failed=campaign.failed_count,
        pending=max(campaign.total_recipients - campaign.sent_count - campaign.failed_count, 0),
    )


def campaign_summary_response(campaign: EmailCampaign) -> CampaignSummary:
    return CampaignSummary(
        **campaign_status_response(campaign).model_dump(),
        subject=campaign.subject,
        template_id=campaign.template_id,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


def campaign_event_payload(campaign: EmailCampaign) -> dict[str, object]:
    return {
        "campaign_id": campaign.id,
        "status": campaign.status,
        "total": campaign.total_recipients,
        "sent": campaign.sent_count,
        "failed": campaign.failed_count,
        "pending": max(campaign.total_recipients - campaign.sent_count - campaign.failed_count, 0),
        "subject": campaign.subject,
        "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None,
    }


def email_log_response(log: EmailLog) -> EmailLogRead:
    supplier = log.supplier
    return EmailLogRead(
        id=log.id,
        campaign_id=log.campaign_id,
        supplier_id=log.supplier_id,
        supplier_name=supplier.supplier_name if supplier else None,
        supplier_company=supplier.company if supplier else None,
        to_email=log.to_email,
        status=log.status,
        provider_response=log.provider_response,
        error_message=log.error_message,
        sent_at=log.sent_at,
    )


def eligible_suppliers_query(db: Session, profile_id: int):
    return db.query(Supplier).filter(
        scoped_profile_filter(Supplier, profile_id, db),
        Supplier.email.isnot(None),
        Supplier.is_valid_email.is_(True),
        Supplier.status != "email_sent",
    )


@router.get("/eligible-suppliers", response_model=SupplierListResponse)
def list_eligible_suppliers(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> SupplierListResponse:
    query = eligible_suppliers_query(db, profile_id)

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

    suppliers = query.order_by(Supplier.created_at.desc(), Supplier.id.desc()).all()
    deduped_suppliers = dedupe_sendable_suppliers(suppliers)
    start = (page - 1) * page_size
    end = start + page_size

    return SupplierListResponse(
        items=deduped_suppliers[start:end],
        total=len(deduped_suppliers),
        page=page,
        page_size=page_size,
    )


@router.post("/send/{supplier_id}", response_model=EmailSendResponse)
def send_email_to_supplier(
    supplier_id: int,
    payload: SendEmailRequest | None = None,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
    email_service: EmailJSService = Depends(get_email_service),
) -> EmailSendResponse:
    supplier = db.query(Supplier).filter(scoped_profile_filter(Supplier, profile_id, db), Supplier.id == supplier_id).first()
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")

    if not is_supplier_sendable(supplier):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier does not have a valid email.")

    subject = (payload.subject if payload and payload.subject else DEFAULT_EMAIL_SUBJECT)
    template_id = normalize_template_id(payload.template_id if payload else None)
    log = send_supplier_email(db, supplier, subject, template_id, email_service, profile_id=profile_id)

    return EmailSendResponse(
        success=log.status == "sent",
        supplier_id=supplier.id,
        email_log_id=log.id,
        status=log.status,
        error=log.error_message,
    )


@router.post("/campaigns", response_model=CampaignStatusResponse)
def create_email_campaign(
    payload: CreateEmailCampaignRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> CampaignStatusResponse:
    suppliers = (
        db.query(Supplier).filter(scoped_profile_filter(Supplier, profile_id, db), Supplier.id.in_(payload.supplier_ids)).all()
        if payload.supplier_ids
        else []
    )
    subject = payload.subject or DEFAULT_EMAIL_SUBJECT
    template_id = normalize_template_id(payload.template_id)
    campaign, supplier_ids = create_campaign(db, suppliers, subject, template_id, profile_id)

    if supplier_ids:
        background_tasks.add_task(run_campaign, campaign.id, supplier_ids, subject, template_id, profile_id)

        return campaign_status_response(campaign)


@router.patch("/campaigns/{campaign_id}/cancel", response_model=CampaignStatusResponse)
def cancel_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> CampaignStatusResponse:
    campaign = db.query(EmailCampaign).filter(scoped_profile_filter(EmailCampaign, profile_id, db), EmailCampaign.id == campaign_id).first()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    if campaign.status in {"completed", "failed", "error", "canceled"}:
        return campaign_status_response(campaign)

    campaign.status = "canceled"
    campaign.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)
    publish_realtime_event_sync("email_campaign.updated", campaign_event_payload(campaign), profile_id)
    return campaign_status_response(campaign)


@router.post("/campaigns/valid-suppliers", response_model=CampaignStatusResponse)
def create_campaign_for_valid_suppliers(
    background_tasks: BackgroundTasks,
    payload: SendEmailRequest | None = None,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> CampaignStatusResponse:
    suppliers = (
        db.query(Supplier)
        .filter(
            scoped_profile_filter(Supplier, profile_id, db),
            Supplier.email.isnot(None),
            Supplier.is_valid_email.is_(True),
            Supplier.status != "email_sent",
        )
        .all()
    )
    subject = (payload.subject if payload and payload.subject else DEFAULT_EMAIL_SUBJECT)
    template_id = normalize_template_id(payload.template_id if payload else None)
    campaign, supplier_ids = create_campaign(db, suppliers, subject, template_id, profile_id)

    if supplier_ids:
        background_tasks.add_task(run_campaign, campaign.id, supplier_ids, subject, template_id, profile_id)

    return campaign_status_response(campaign)


@router.get("/campaigns", response_model=CampaignListResponse)
def list_email_campaigns(
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> CampaignListResponse:
    query = db.query(EmailCampaign).filter(scoped_profile_filter(EmailCampaign, profile_id, db))

    if status_filter:
        query = query.filter(EmailCampaign.status == status_filter)

    total = query.count()
    campaigns = (
        query.order_by(EmailCampaign.created_at.desc(), EmailCampaign.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return CampaignListResponse(
        items=[campaign_summary_response(campaign) for campaign in campaigns],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/campaigns/{campaign_id}", response_model=CampaignStatusResponse)
def get_campaign_status(
    campaign_id: int,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> CampaignStatusResponse:
    campaign = db.query(EmailCampaign).filter(scoped_profile_filter(EmailCampaign, profile_id, db), EmailCampaign.id == campaign_id).first()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    return campaign_status_response(campaign)


@router.get("/logs", response_model=list[EmailLogRead])
def list_email_logs(
    supplier_id: int | None = Query(default=None),
    campaign_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> list[EmailLog]:
    query = db.query(EmailLog).filter(scoped_profile_filter(EmailLog, profile_id, db))

    if supplier_id is not None:
        query = query.filter(EmailLog.supplier_id == supplier_id)
    if campaign_id is not None:
        query = query.filter(EmailLog.campaign_id == campaign_id)
    if status_filter:
        query = query.filter(EmailLog.status == status_filter)

    logs = query.order_by(EmailLog.id.desc()).all()
    return [email_log_response(log) for log in logs]
