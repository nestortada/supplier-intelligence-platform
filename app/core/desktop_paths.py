import os
import sys
from pathlib import Path


TRUTHY_VALUES = {"1", "true", "yes", "on"}


def is_desktop_mode() -> bool:
    return os.getenv("SUPPLIERINTEL_DESKTOP", "").strip().lower() in TRUTHY_VALUES


def app_data_dir() -> Path:
    override = os.getenv("SUPPLIERINTEL_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser()

    if sys.platform == "win32":
        base = os.getenv("APPDATA")
        if base:
            return Path(base) / "SupplierIntel"
        return Path.home() / "AppData" / "Roaming" / "SupplierIntel"

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "SupplierIntel"

    return Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "SupplierIntel"


def ensure_app_data_dir() -> Path:
    data_dir = app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def desktop_data_file(filename: str) -> Path:
    return ensure_app_data_dir() / filename


def desktop_sqlite_url(filename: str = "supplier_intelligence.db") -> str:
    return f"sqlite:///{desktop_data_file(filename).as_posix()}"


def desktop_env_file() -> Path:
    return desktop_data_file(".env")


def bundled_env_file() -> Path | None:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if not bundle_root:
        return None

    path = Path(bundle_root) / ".env"
    return path if path.exists() else None
