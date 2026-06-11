from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.sync_service import SyncService


router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status")
def get_sync_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    return SyncService(db).status()


@router.post("/run")
def run_sync(db: Session = Depends(get_db)) -> dict[str, Any]:
    return SyncService(db).run_once()
