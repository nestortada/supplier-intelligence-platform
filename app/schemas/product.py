from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


ProductStatus = Literal[
    "pending_analysis",
    "enriched",
    "analyzed",
    "buy",
    "review",
    "discard",
    "insufficient_data",
]


class ProductBase(BaseModel):
    supplier_id: int | None = None
    product_name: str | None = None
    description: str | None = None
    sku: str | None = None
    upc: str | None = None
    ean: str | None = None
    gtin: str | None = None
    brand: str | None = None
    category: str | None = None
    supplier_cost: Decimal | None = None
    case_quantity: int | None = None
    uom: str | None = None
    raw_row_json: str | None = None
    status: str = "pending_analysis"


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    supplier_id: int | None = None
    product_name: str | None = None
    description: str | None = None
    sku: str | None = None
    upc: str | None = None
    ean: str | None = None
    gtin: str | None = None
    brand: str | None = None
    category: str | None = None
    supplier_cost: Decimal | None = None
    case_quantity: int | None = None
    uom: str | None = None
    raw_row_json: str | None = None
    status: str | None = None


class ProductRead(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    page_size: int


class BulkUpdateStatusRequest(BaseModel):
    product_ids: list[int]
    status: ProductStatus


class BulkUpdateStatusResponse(BaseModel):
    success: bool
    updated: int


class ProductDatabaseClearResponse(BaseModel):
    success: bool
    products_deleted: int
    amazon_data_deleted: int
    analyses_deleted: int


class EnrichApifyRequest(BaseModel):
    product_ids: list[int] | None = None
    lookup_by: Literal["auto"] = "auto"
    all_pending: bool = False
    force_refresh: bool = False
    run_analysis_after: bool = False


class EnrichApifyResponse(BaseModel):
    success: bool
    job_id: int
    total_items: int
    status: str


class AnalyzeProductsRequest(BaseModel):
    product_ids: list[int] | None = None
    all: bool = False


class AnalyzeProductsResponse(BaseModel):
    success: bool
    job_id: int
    total_items: int
    status: str


class AmazonProductDataBase(BaseModel):
    product_id: int
    asin: str | None = None
    amazon_title: str | None = None
    amazon_url: str | None = None
    image_url: str | None = None
    current_price: Decimal | None = None
    buybox_price: Decimal | None = None
    amazon_price: Decimal | None = None
    list_price: Decimal | None = None
    currency: str | None = None
    rating: Decimal | None = None
    reviews_count: int | None = None
    sellers_count: int | None = None
    estimated_sales: int | None = None
    price_history_json: str | None = None
    sellers_history_json: str | None = None
    raw_response_json: str | None = None


class AmazonProductDataCreate(AmazonProductDataBase):
    pass


class AmazonProductDataRead(AmazonProductDataBase):
    id: int
    captured_at: datetime

    model_config = ConfigDict(from_attributes=True)
