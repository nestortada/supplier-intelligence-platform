import argparse
import base64
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.encrypted_env import protect_windows_dpapi


def default_destination() -> Path:
    appdata = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    return appdata / "SupplierIntel" / ".env.enc"


def main() -> int:
    parser = argparse.ArgumentParser(description="Encrypt a SupplierIntel desktop .env file with Windows DPAPI.")
    parser.add_argument("--source", default=".env", help="Plaintext .env file to encrypt.")
    parser.add_argument("--destination", default=str(default_destination()), help="Destination .env.enc path.")
    args = parser.parse_args()

    if sys.platform != "win32":
        parser.error("DPAPI encryption is only available on Windows.")

    source = Path(args.source).expanduser().resolve()
    destination = Path(args.destination).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    encrypted = protect_windows_dpapi(source.read_bytes())
    destination.write_text(base64.b64encode(encrypted).decode("ascii"), encoding="utf-8")

    print(f"Encrypted desktop env written to {destination}")
    print("It can only be decrypted by the same Windows user account on this computer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
