from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("user_profiles.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    processed_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sync_id: Mapped[str | None] = mapped_column(String(64), default=lambda: uuid4().hex, unique=True, index=True)
    sync_updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    sync_deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    profile = relationship("UserProfile", back_populates="background_jobs")
