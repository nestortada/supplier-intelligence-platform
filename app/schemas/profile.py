from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    avatar_data_url: str | None = Field(default=None, max_length=1_500_000)


class UserProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    avatar_data_url: str | None = Field(default=None, max_length=1_500_000)


class UserProfileRead(BaseModel):
    id: int
    name: str
    avatar_data_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileDeleteResponse(BaseModel):
    success: bool
    active_profile: UserProfileRead | None = None
