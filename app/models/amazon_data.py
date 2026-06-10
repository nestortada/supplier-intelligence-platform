from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AmazonProductData(Base):
    __tablename__ = "amazon_product_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    asin: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    amazon_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    amazon_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    buybox_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    amazon_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    list_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    reviews_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sellers_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_sales: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_history_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    sellers_history_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="amazon_data")
