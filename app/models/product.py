from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("user_profiles.id"), nullable=True, index=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True, index=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    upc: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    ean: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    gtin: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    brand: Mapped[str | None] = mapped_column(String(160), nullable=True)
    category: Mapped[str | None] = mapped_column(String(160), nullable=True)
    supplier_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    case_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uom: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_row_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending_analysis", index=True)
    selected_for_sale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    sale_performance: Mapped[str | None] = mapped_column(String(20), nullable=True)
    selected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sync_id: Mapped[str | None] = mapped_column(String(64), default=lambda: uuid4().hex, unique=True, index=True)
    sync_updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    sync_deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    profile = relationship("UserProfile", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    amazon_data = relationship("AmazonProductData", back_populates="product", cascade="all, delete-orphan")
    analyses = relationship("ProductAnalysis", back_populates="product", cascade="all, delete-orphan")
