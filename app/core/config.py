from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Supplier Intelligence Platform"
    DATABASE_URL: str = "sqlite:///./supplier_intelligence.db"

    EMAILJS_SERVICE_ID: str = ""
    EMAILJS_TEMPLATE_ID: str = ""
    EMAILJS_PUBLIC_KEY: str = ""
    EMAILJS_PRIVATE_KEY: str = ""
    EMAILJS_API_URL: str = "https://api.emailjs.com/api/v1.0/email/send"

    APIFY_TOKEN: str = ""
    APIFY_ACTOR_ID: str = ""
    APIFY_USER_ID: str = ""
    APIFY_API_BASE_URL: str = "https://api.apify.com/v2"

    MY_NAME: str = ""
    MY_EMAIL: str = ""
    MY_PHONE: str = ""

    MAX_UPLOAD_SIZE_MB: int = 10
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
