from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProductAnalysis(Base):
    __tablename__ = "product_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    net_profit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    margin: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    roi: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    profitability_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    roi_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    sales_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    price_stability_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    sellers_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    data_quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    final_opportunity_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    recommendation_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    recommendation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    risks_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sync_id: Mapped[str | None] = mapped_column(String(64), default=lambda: uuid4().hex, unique=True, index=True)
    sync_updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    sync_deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    product = relationship("Product", back_populates="analyses")
