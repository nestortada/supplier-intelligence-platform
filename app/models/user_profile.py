from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_data_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    suppliers = relationship("Supplier", back_populates="profile")
    products = relationship("Product", back_populates="profile")
    email_campaigns = relationship("EmailCampaign", back_populates="profile")
    email_logs = relationship("EmailLog", back_populates="profile")
    background_jobs = relationship("BackgroundJob", back_populates="profile")
