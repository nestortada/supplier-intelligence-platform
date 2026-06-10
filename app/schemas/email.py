from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmailCampaignBase(BaseModel):
    subject: str | None = None
    template_id: str | None = None
    status: str = "draft"
    total_recipients: int = 0
    sent_count: int = 0
    failed_count: int = 0


class EmailCampaignCreate(EmailCampaignBase):
    pass


class EmailCampaignRead(EmailCampaignBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailLogBase(BaseModel):
    campaign_id: int | None = None
    supplier_id: int | None = None
    to_email: str | None = None
    status: str = "pending"
    provider_response: str | None = None
    error_message: str | None = None
    sent_at: datetime | None = None


class EmailLogCreate(EmailLogBase):
    pass


class EmailLogRead(EmailLogBase):
    id: int
    supplier_name: str | None = None
    supplier_company: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SendEmailRequest(BaseModel):
    subject: str | None = None
    template_id: str | None = None


class CreateEmailCampaignRequest(BaseModel):
    supplier_ids: list[int] = Field(default_factory=list)
    template_id: str | None = None
    subject: str | None = None


class CampaignStatusResponse(BaseModel):
    campaign_id: int
    status: str
    total: int
    sent: int
    failed: int
    pending: int


class CampaignSummary(CampaignStatusResponse):
    subject: str | None = None
    template_id: str | None = None
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    items: list[CampaignSummary]
    total: int
    page: int
    page_size: int


class EmailSendResponse(BaseModel):
    success: bool
    supplier_id: int
    email_log_id: int | None = None
    status: str
    error: str | None = None
