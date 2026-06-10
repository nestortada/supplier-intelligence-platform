from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SupplierBase(BaseModel):
    supplier_name: str | None = None
    company: str | None = None
    email: str | None = None
    website: str | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    category: str | None = None
    status: str = "pending"
    is_valid_email: bool = False
    notes: str | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    supplier_name: str | None = None
    company: str | None = None
    email: str | None = None
    website: str | None = None
    phone: str | None = None
    city: str | None = None
    country: str | None = None
    category: str | None = None
    status: str | None = None
    is_valid_email: bool | None = None
    notes: str | None = None


class SupplierRead(SupplierBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierListResponse(BaseModel):
    items: list[SupplierRead]
    total: int
    page: int
    page_size: int


class SupplierUploadResponse(BaseModel):
    success: bool
    total_rows: int
    valid_emails: int
    invalid_emails: int
    duplicates_removed: int
    suppliers_created: int
    suppliers_skipped: int


class SupplierDatabaseClearResponse(BaseModel):
    success: bool
    suppliers_deleted: int
    products_deleted: int
    email_logs_deleted: int
    email_campaigns_deleted: int
