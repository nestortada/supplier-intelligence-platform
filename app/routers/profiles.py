from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.profiles import get_active_profile_id, get_or_create_default_profile, scoped_profile_filter
from app.models.amazon_data import AmazonProductData
from app.models.analysis import ProductAnalysis
from app.models.background_job import BackgroundJob
from app.models.email_campaign import EmailCampaign, EmailLog
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.user_profile import UserProfile
from app.schemas.profile import UserProfileCreate, UserProfileDeleteResponse, UserProfileRead, UserProfileUpdate


router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=list[UserProfileRead])
def list_profiles(db: Session = Depends(get_db)) -> list[UserProfile]:
    get_or_create_default_profile(db)
    return db.query(UserProfile).order_by(UserProfile.created_at.asc(), UserProfile.id.asc()).all()


@router.post("", response_model=UserProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(payload: UserProfileCreate, db: Session = Depends(get_db)) -> UserProfile:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile name is required.")

    profile = UserProfile(name=name, avatar_data_url=payload.avatar_data_url)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/{profile_id}", response_model=UserProfileRead)
def update_profile(
    profile_id: int,
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    active_profile_id: int = Depends(get_active_profile_id),
) -> UserProfile:
    if profile_id != active_profile_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update another profile.")

    profile = db.get(UserProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile name is required.")

    profile.name = name
    profile.avatar_data_url = payload.avatar_data_url
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}", response_model=UserProfileDeleteResponse)
def delete_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    active_profile_id: int = Depends(get_active_profile_id),
) -> UserProfileDeleteResponse:
    if profile_id != active_profile_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete another profile.")

    profile = db.get(UserProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

    product_ids = [
        product_id
        for (product_id,) in db.query(Product.id).filter(scoped_profile_filter(Product, profile_id, db)).all()
    ]

    if product_ids:
        db.query(ProductAnalysis).filter(ProductAnalysis.product_id.in_(product_ids)).delete(synchronize_session=False)
        db.query(AmazonProductData).filter(AmazonProductData.product_id.in_(product_ids)).delete(synchronize_session=False)

    db.query(EmailLog).filter(scoped_profile_filter(EmailLog, profile_id, db)).delete(synchronize_session=False)
    db.query(EmailCampaign).filter(scoped_profile_filter(EmailCampaign, profile_id, db)).delete(synchronize_session=False)
    db.query(BackgroundJob).filter(scoped_profile_filter(BackgroundJob, profile_id, db)).delete(synchronize_session=False)
    db.query(Product).filter(scoped_profile_filter(Product, profile_id, db)).delete(synchronize_session=False)
    db.query(Supplier).filter(scoped_profile_filter(Supplier, profile_id, db)).delete(synchronize_session=False)
    db.delete(profile)
    db.commit()

    next_profile = db.query(UserProfile).order_by(UserProfile.created_at.asc(), UserProfile.id.asc()).first()
    if next_profile is None:
        next_profile = get_or_create_default_profile(db)

    return UserProfileDeleteResponse(success=True, active_profile=next_profile)
