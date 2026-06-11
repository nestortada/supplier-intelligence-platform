from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.desktop_paths import bundled_env_file, desktop_env_file, desktop_sqlite_url, is_desktop_mode
from app.core.encrypted_env import load_encrypted_desktop_env


load_encrypted_desktop_env()

DEFAULT_DATABASE_URL = desktop_sqlite_url() if is_desktop_mode() else "sqlite:///./supplier_intelligence.db"
DESKTOP_ENV_FILES = tuple(
    str(path)
    for path in (
        bundled_env_file(),
        desktop_env_file(),
    )
    if path is not None
)
ENV_FILES = DESKTOP_ENV_FILES if is_desktop_mode() else ".env"


class Settings(BaseSettings):
    APP_NAME: str = "Supplier Intelligence Platform"
    DATABASE_URL: str = DEFAULT_DATABASE_URL

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

    FIREBASE_ENABLED: bool = False
    FIREBASE_CREDENTIALS_PATH: str = ""
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_NAMESPACE: str = "default"
    FIREBASE_SYNC_INTERVAL_SECONDS: int = 60

    WEBHOOK_SECRET: str = ""

    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8765",
            "http://127.0.0.1:18765",
            "http://tauri.localhost",
            "https://tauri.localhost",
        ]
    )

    model_config = SettingsConfigDict(env_file=ENV_FILES, env_file_encoding="utf-8", extra="ignore")


settings = Settings()
