from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("user_profiles.id"), nullable=True, index=True)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    is_valid_email: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sync_id: Mapped[str | None] = mapped_column(String(64), default=lambda: uuid4().hex, unique=True, index=True)
    sync_updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    sync_deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    profile = relationship("UserProfile", back_populates="suppliers")
    products = relationship("Product", back_populates="supplier", cascade="all, delete-orphan")
    email_logs = relationship("EmailLog", back_populates="supplier")
