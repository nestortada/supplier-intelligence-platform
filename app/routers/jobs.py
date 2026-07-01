import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.profiles import get_active_profile_id, scoped_profile_filter
from app.models.background_job import BackgroundJob
from app.schemas.analysis import JobStatusResponse
from app.core.realtime import publish_realtime_event_sync


router = APIRouter(prefix="/jobs", tags=["jobs"])


def job_error_items(job: BackgroundJob) -> list[dict[str, object]]:
    if not job.error_items_json:
        return []
    try:
        parsed = json.loads(job.error_items_json)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def job_status_response(job: BackgroundJob) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=job.id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        total_items=job.total_items,
        processed_items=job.processed_items,
        failed_items=job.failed_items,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        error_items=job_error_items(job),
    )


def job_event_payload(job: BackgroundJob) -> dict[str, object]:
    return {
        "job_id": job.id,
        "type": job.type,
        "status": job.status,
        "progress": job.progress,
        "total_items": job.total_items,
        "processed_items": job.processed_items,
        "failed_items": job.failed_items,
        "error_message": job.error_message,
        "error_items": job_error_items(job),
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.get("", response_model=list[JobStatusResponse])
def list_jobs(
    type_filter: Annotated[str | None, Query(alias="type")] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> list[JobStatusResponse]:
    query = db.query(BackgroundJob).filter(scoped_profile_filter(BackgroundJob, profile_id, db))
    if type_filter:
        query = query.filter(BackgroundJob.type == type_filter)
    if status_filter:
        query = query.filter(BackgroundJob.status == status_filter)

    return [job_status_response(job) for job in query.order_by(BackgroundJob.created_at.desc(), BackgroundJob.id.desc()).all()]


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> JobStatusResponse:
    job = db.query(BackgroundJob).filter(scoped_profile_filter(BackgroundJob, profile_id, db), BackgroundJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return job_status_response(job)


@router.patch("/{job_id}/cancel", response_model=JobStatusResponse)
def cancel_job(
    job_id: int,
    db: Session = Depends(get_db),
    profile_id: int = Depends(get_active_profile_id),
) -> JobStatusResponse:
    job = db.query(BackgroundJob).filter(scoped_profile_filter(BackgroundJob, profile_id, db), BackgroundJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job.status in {"completed", "failed", "error", "canceled"}:
        return job_status_response(job)

    job.status = "canceled"
    job.progress = 100
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    publish_realtime_event_sync("job.updated", job_event_payload(job), profile_id)
    return job_status_response(job)
