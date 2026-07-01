import os
from pathlib import Path

import uvicorn
from dotenv import dotenv_values

os.environ.setdefault("SUPPLIERINTEL_DESKTOP", "1")

if os.getenv("SUPPLIERINTEL_DESKTOP", "").strip().lower() in {"1", "true", "yes", "on"}:
    from app.core.desktop_paths import install_bundled_data_file

    installed_env = install_bundled_data_file(".env")
    if installed_env is not None:
        firebase_credentials_path = dotenv_values(installed_env).get("FIREBASE_CREDENTIALS_PATH")
        if firebase_credentials_path:
            install_bundled_data_file(Path(firebase_credentials_path).name)

if "DATABASE_URL" not in os.environ:
    from app.core.desktop_paths import desktop_sqlite_url

    os.environ["DATABASE_URL"] = desktop_sqlite_url()

from app.main import app


def main() -> None:
    host = os.getenv("SUPPLIERINTEL_DESKTOP_HOST", "127.0.0.1")
    port = int(os.getenv("SUPPLIERINTEL_DESKTOP_PORT", "18765"))
    log_level = os.getenv("SUPPLIERINTEL_LOG_LEVEL", "info")

    uvicorn.run(app, host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    main()
