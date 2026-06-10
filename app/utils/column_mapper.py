import re
from collections.abc import Iterable
from typing import Any


COLUMN_ALIASES = {
    "supplier_name": ["supplier", "supplier name", "name", "contact name", "vendor", "distributor"],
    "company": ["company", "company name", "business", "distributor name", "supplier company"],
    "email": ["email", "e-mail", "mail", "contact email", "email address"],
    "website": ["website", "web", "url", "site", "company website"],
    "phone": ["phone", "telephone", "mobile", "contact number"],
    "city": ["city", "location", "town"],
    "country": ["country", "nation"],
    "category": ["category", "product category", "type", "industry"],
}


def normalize_column_name(name: Any) -> str:
    text = "" if name is None else str(name)
    text = text.strip().lower()
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("e mail", "email")


def map_columns(headers: Iterable[Any]) -> dict[str, str]:
    normalized_headers = {normalize_column_name(header): str(header) for header in headers}
    mapped: dict[str, str] = {}

    for field_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_column_name(alias)
            if normalized_alias in normalized_headers:
                mapped[field_name] = normalized_headers[normalized_alias]
                break

    return mapped
