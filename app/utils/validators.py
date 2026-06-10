import re
from typing import Any


EMAIL_REGEX = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    try:
        if value != value:
            return None
    except TypeError:
        pass

    text = re.sub(r"[\x00-\x1f\x7f]", " ", str(value)).strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return None

    return text


def normalize_email(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    return text.lower()


def is_valid_email(value: Any) -> bool:
    email = normalize_email(value)
    if email is None:
        return False
    return bool(EMAIL_REGEX.fullmatch(email))


def _clean_digits(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".", 1)[0]

    digits = re.sub(r"\D", "", text)
    return digits or None


def clean_upc(value: Any) -> str | None:
    return _clean_digits(value)


def clean_ean(value: Any) -> str | None:
    return _clean_digits(value)


def clean_price(value: Any) -> float | None:
    text = clean_text(value)
    if text is None:
        return None

    cleaned = re.sub(r"[^0-9,.\-]", "", text)
    if not cleaned or cleaned in {"-", ".", ",", "-.", "-,"}:
        return None

    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        whole, _, decimals = cleaned.rpartition(",")
        if whole and len(decimals) in {1, 2}:
            cleaned = f"{whole.replace(',', '')}.{decimals}"
        else:
            cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return None
