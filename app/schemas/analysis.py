from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductAnalysisBase(BaseModel):
    product_id: int
    net_profit: Decimal | None = None
    margin: Decimal | None = None
    roi: Decimal | None = None
    profitability_score: Decimal | None = None
    roi_score: Decimal | None = None
    sales_score: Decimal | None = None
    price_stability_score: Decimal | None = None
    sellers_score: Decimal | None = None
    data_quality_score: Decimal | None = None
    final_opportunity_score: Decimal | None = None
    recommendation_status: str | None = None
    recommendation_reason: str | None = None
    risks_json: str | None = None


class ProductAnalysisCreate(ProductAnalysisBase):
    pass


class ProductAnalysisRead(ProductAnalysisBase):
    id: int
    analyzed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BackgroundJobBase(BaseModel):
    type: str
    status: str = "pending"
    progress: int = 0
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    error_message: str | None = None


class BackgroundJobCreate(BackgroundJobBase):
    pass


class BackgroundJobRead(BackgroundJobBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    job_id: int
    type: str
    status: str
    progress: int
    total_items: int
    processed_items: int
    failed_items: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
