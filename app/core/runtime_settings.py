import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.core.desktop_paths import desktop_data_file, is_desktop_mode


DEFAULT_SCORING_WEIGHTS = {
    "profitability": 0.30,
    "roi": 0.20,
    "sales": 0.20,
    "price_stability": 0.15,
    "sellers": 0.10,
    "data_quality": 0.05,
}

DEFAULT_FEES = {
    "referral_fee_rate": 0.15,
    "default_fba_fee": 4.50,
    "default_shipping_cost": 0.75,
    "default_prep_fee": 0.50,
    "default_other_costs": 0.50,
}

SETTINGS_FILE = desktop_data_file("app_runtime_settings.json") if is_desktop_mode() else Path("app_runtime_settings.json")


class RuntimeSettingsError(ValueError):
    pass


class RuntimeSettingsService:
    def __init__(self, path: Path | str = SETTINGS_FILE) -> None:
        self.path = Path(path)

    def get_scoring(self) -> dict[str, float]:
        return self._load()["scoring"]

    def update_scoring(self, values: dict[str, Any]) -> dict[str, float]:
        scoring = self._validate_exact_positive_numbers(values, set(DEFAULT_SCORING_WEIGHTS), "scoring")
        total = sum(Decimal(str(value)) for value in scoring.values())
        if abs(total - Decimal("1.0")) > Decimal("0.0001"):
            raise RuntimeSettingsError("Scoring weights must sum to 1.0.")

        data = self._load()
        data["scoring"] = scoring
        self._save(data)
        return scoring

    def get_fees(self) -> dict[str, float]:
        return self._load()["fees"]

    def update_fees(self, values: dict[str, Any]) -> dict[str, float]:
        fees = self._validate_exact_positive_numbers(values, set(DEFAULT_FEES), "fees")
        data = self._load()
        data["fees"] = fees
        self._save(data)
        return fees

    def _load(self) -> dict[str, dict[str, float]]:
        data = self._defaults()
        if not self.path.exists():
            return data

        try:
            stored = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return data

        if isinstance(stored, dict):
            if isinstance(stored.get("scoring"), dict):
                try:
                    data["scoring"] = self._validate_exact_positive_numbers(
                        stored["scoring"], set(DEFAULT_SCORING_WEIGHTS), "scoring"
                    )
                except RuntimeSettingsError:
                    pass
            if isinstance(stored.get("fees"), dict):
                try:
                    data["fees"] = self._validate_exact_positive_numbers(stored["fees"], set(DEFAULT_FEES), "fees")
                except RuntimeSettingsError:
                    pass
        return data

    def _save(self, data: dict[str, dict[str, float]]) -> None:
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _defaults() -> dict[str, dict[str, float]]:
        return {
            "scoring": dict(DEFAULT_SCORING_WEIGHTS),
            "fees": dict(DEFAULT_FEES),
        }

    @staticmethod
    def _validate_exact_positive_numbers(values: dict[str, Any], expected_keys: set[str], label: str) -> dict[str, float]:
        provided_keys = set(values)
        missing = expected_keys - provided_keys
        extra = provided_keys - expected_keys
        if missing:
            raise RuntimeSettingsError(f"Missing {label} keys: {', '.join(sorted(missing))}.")
        if extra:
            raise RuntimeSettingsError(f"Unknown {label} keys: {', '.join(sorted(extra))}.")

        normalized = {}
        for key in sorted(expected_keys):
            try:
                value = Decimal(str(values[key]))
            except (InvalidOperation, ValueError):
                raise RuntimeSettingsError(f"{key} must be a number.") from None
            if value <= 0:
                raise RuntimeSettingsError(f"{key} must be positive.")
            normalized[key] = float(value)
        return normalized


def get_runtime_settings_service() -> RuntimeSettingsService:
    return RuntimeSettingsService()
