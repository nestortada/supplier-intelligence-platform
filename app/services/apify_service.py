import json
import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import settings
from app.models.amazon_data import AmazonProductData
from app.models.product import Product
from app.utils.validators import clean_price, clean_text


logger = logging.getLogger(__name__)

TEMPORARY_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class ApifyServiceError(Exception):
    pass


def _latest_asin(product: Product) -> str | None:
    amazon_rows = sorted(
        [row for row in product.amazon_data if row.asin],
        key=lambda row: row.captured_at or datetime.min,
        reverse=True,
    )
    return amazon_rows[0].asin if amazon_rows else None


def _sku_search_identifier(product: Product) -> str | None:
    sku = clean_text(product.sku)
    if not sku:
        return None

    normalized = sku.lower()
    if "amazon." in normalized or "/dp/" in normalized or normalized.startswith(("http://", "https://")):
        return sku

    if len(sku) == 10 and sku.upper().startswith("B0"):
        return sku

    return None


def _search_keyword(product: Product) -> str | None:
    for value in (
        product.product_name,
        " ".join(part for part in (clean_text(product.brand), clean_text(product.category)) if part),
        _sku_search_identifier(product),
        _latest_asin(product),
        product.upc,
        product.ean,
        product.gtin,
    ):
        keyword = clean_text(value)
        if keyword:
            return keyword
    return None


def build_apify_input(product: Product) -> dict[str, Any]:
    sku_id = _sku_search_identifier(product)
    asin = _latest_asin(product)

    asins = []
    start_urls = []

    if sku_id and ("amazon." in sku_id.lower() or "/dp/" in sku_id.lower() or sku_id.lower().startswith(("http://", "https://"))):
        start_urls.append({"url": sku_id})
        import re
        asin_match = re.search(r"/dp/([A-Z0-9]{10})", sku_id, re.IGNORECASE)
        if asin_match:
            asins.append(asin_match.group(1).upper())
    elif sku_id:
        asins.append(sku_id.upper())
        start_urls.append({"url": f"https://www.amazon.com/dp/{sku_id}"})

    if asin and asin.upper() not in [a.upper() for a in asins]:
        asins.append(asin.upper())
        if not any(f"/dp/{asin}" in u["url"] for u in start_urls):
            start_urls.append({"url": f"https://www.amazon.com/dp/{asin}"})

    if asins or start_urls:
        return {
            "asins": asins,
            "fullDetails": True,
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
            "startUrls": start_urls,
        }

    keyword = _search_keyword(product)
    return {
        "keywords": [keyword] if keyword else [],
        "maxResultsPerKeyword": 50,
        "fullDetails": True,
        "marketplace": "com",
        "concurrency": 4,
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
        },
    }


def build_apify_tracking_input(product: Product, fallback_asin: str | None = None) -> dict[str, Any]:
    identifiers: list[str] = []
    sku_id = _sku_search_identifier(product)
    asin = _latest_asin(product)

    for value in (sku_id, asin, fallback_asin):
        identifier = clean_text(value)
        if identifier and identifier.upper() not in [item.upper() for item in identifiers]:
            identifiers.append(identifier)

    return {
        "identifiers": identifiers,
        "include_variants": False,
        "stream_output": True,
    }


def _decimal_value(value: Any) -> Decimal | None:
    cleaned = clean_price(value)
    if cleaned is None:
        return None
    return Decimal(str(cleaned))


def _int_value(value: Any) -> int | None:
    cleaned = clean_price(value)
    if cleaned is None:
        return None
    return int(cleaned)


def _quantity_value(value: Any) -> int | None:
    text = clean_text(value)
    if text is None:
        return None

    multiplier = 1
    normalized = text.upper()
    if "K" in normalized:
        multiplier = 1_000
    elif "M" in normalized:
        multiplier = 1_000_000

    cleaned = clean_price(text)
    if cleaned is None:
        return None
    return int(cleaned * multiplier)


def _json_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True, default=str)


def _first_text(value: Any) -> str | None:
    if isinstance(value, list):
        for item in value:
            text = clean_text(item)
            if text:
                return text
        return None
    return clean_text(value)


def _merge_apify_items(detail_item: dict[str, Any] | None, tracking_item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not detail_item and not tracking_item:
        return None

    merged: dict[str, Any] = {}
    for item in (tracking_item, detail_item):
        if item:
            merged.update({key: value for key, value in item.items() if value is not None})

    if tracking_item:
        for key in (
            "price_new_history",
            "price_new_fba_history",
            "price_amazon_history",
            "price_buybox_history",
            "price_prime_exclusive_history",
            "n_offers_new_history",
            "variant_asins",
            "variant_upcs",
            "variant_eans",
            "data_captured_at",
            "last_updated",
            "tracked_since",
            "listed_at",
        ):
            if tracking_item.get(key) is not None:
                merged[key] = tracking_item[key]

    merged["apify_detail_actor_item"] = detail_item
    merged["apify_tracking_actor_item"] = tracking_item
    return merged


def map_apify_item_to_amazon_data(product_id: int, data: dict[str, Any]) -> AmazonProductData:
    price_history = (
        data.get("price_new_history")
        or data.get("price_buybox_history")
        or data.get("price_amazon_history")
    )

    return AmazonProductData(
        product_id=product_id,
        asin=clean_text(data.get("asin")),
        amazon_title=clean_text(data.get("name") or data.get("title")),
        amazon_url=clean_text(data.get("product_url") or data.get("url")),
        image_url=_first_text(data.get("image_url") or data.get("thumbnail_url") or data.get("images")),
        current_price=_decimal_value(data.get("price") or data.get("current_price")),
        buybox_price=_decimal_value(data.get("price_buybox")),
        amazon_price=_decimal_value(data.get("price_amazon")),
        list_price=_decimal_value(data.get("list_price")),
        currency=clean_text(data.get("currency")),
        rating=_decimal_value(data.get("rating")),
        reviews_count=_int_value(data.get("n_reviews") or data.get("reviews_count") or data.get("review_count")),
        sellers_count=_int_value(data.get("n_offers_new") or data.get("sellers_count")),
        estimated_sales=_quantity_value(
            data.get("estimated_monthly_sales")
            or data.get("estimated_sales")
            or data.get("monthly_sales")
            or data.get("sales")
            or data.get("bought_in_past_month")
        ),
        price_history_json=_json_value(price_history),
        sellers_history_json=_json_value(data.get("n_offers_new_history") or data.get("best_sellers_rank")),
        raw_response_json=json.dumps(data, ensure_ascii=True, default=str),
    )


class ApifyService:
    def __init__(
        self,
        client: httpx.Client | None = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        wait_for_finish_seconds: int = 60,
    ) -> None:
        self.client = client
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.wait_for_finish_seconds = wait_for_finish_seconds

    def run_actor(self, input_data: dict, actor_id: str | None = None) -> dict:
        actor_id = actor_id or settings.APIFY_ACTOR_ID
        missing_settings = self._missing_settings(actor_id=actor_id)
        if missing_settings:
            raise ApifyServiceError(f"Missing Apify settings: {', '.join(missing_settings)}")

        endpoint = f"{settings.APIFY_API_BASE_URL.rstrip('/')}/acts/{actor_id}/runs"
        params = {"token": settings.APIFY_TOKEN, "waitForFinish": self.wait_for_finish_seconds}
        response_data = self._request("POST", endpoint, params=params, json=input_data)
        return response_data.get("data", response_data)

    def get_dataset_items(self, dataset_id: str) -> list[dict]:
        missing_settings = self._missing_settings(require_actor=False)
        if missing_settings:
            raise ApifyServiceError(f"Missing Apify settings: {', '.join(missing_settings)}")

        endpoint = f"{settings.APIFY_API_BASE_URL.rstrip('/')}/datasets/{dataset_id}/items"
        params = {"token": settings.APIFY_TOKEN, "clean": "true"}
        response_data = self._request("GET", endpoint, params=params)

        if isinstance(response_data, list):
            return response_data
        if isinstance(response_data.get("data"), list):
            return response_data["data"]
        return []

    def search_amazon_product(self, product: Product) -> dict | None:
        input_data = build_apify_input(product)
        if not input_data.get("asins") and not input_data.get("startUrls") and not input_data.get("keywords"):
            return None

        detail_item = self._run_actor_first_item(settings.APIFY_ACTOR_ID, input_data, product.id)
        fallback_asin = clean_text(detail_item.get("asin")) if detail_item else None
        tracking_input = build_apify_tracking_input(product, fallback_asin=fallback_asin)
        tracking_item = None
        if tracking_input.get("identifiers"):
            tracking_item = self._run_actor_first_item(settings.APIFY_TRACKING_ACTOR_ID, tracking_input, product.id)

        return _merge_apify_items(detail_item, tracking_item)

    def _run_actor_first_item(self, actor_id: str, input_data: dict[str, Any], product_id: int | None = None) -> dict[str, Any] | None:
        actor_run = self.run_actor(input_data, actor_id=actor_id)
        dataset_id = actor_run.get("defaultDatasetId")
        if not dataset_id:
            logger.warning("apify_run_missing_dataset", extra={"actor_id": actor_id, "product_id": product_id})
            return None

        items = self.get_dataset_items(dataset_id)
        return items[0] if items else None

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)

        try:
            for attempt in range(self.max_retries + 1):
                try:
                    logger.info("apify_request_attempt", extra={"method": method, "attempt": attempt + 1})
                    response = client.request(method, endpoint, **kwargs)
                    if response.status_code < 400:
                        return response.json()

                    if response.status_code in TEMPORARY_STATUS_CODES and attempt < self.max_retries:
                        logger.warning(
                            "apify_temporary_http_error",
                            extra={"method": method, "attempt": attempt + 1, "status_code": response.status_code},
                        )
                        time.sleep(1)
                        continue

                    raise ApifyServiceError(f"Apify HTTP error {response.status_code}: {response.text}")
                except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as exc:
                    if attempt < self.max_retries:
                        logger.warning(
                            "apify_temporary_request_error",
                            extra={"method": method, "attempt": attempt + 1, "error_type": type(exc).__name__},
                        )
                        time.sleep(1)
                        continue
                    raise ApifyServiceError(type(exc).__name__) from exc
        finally:
            if owns_client:
                client.close()

        raise ApifyServiceError("Apify request failed.")

    @staticmethod
    def _missing_settings(require_actor: bool = True, actor_id: str | None = None) -> list[str]:
        required_settings = {
            "APIFY_TOKEN": settings.APIFY_TOKEN,
            "APIFY_API_BASE_URL": settings.APIFY_API_BASE_URL,
        }
        if require_actor:
            required_settings["APIFY_ACTOR_ID"] = actor_id or settings.APIFY_ACTOR_ID
        return [name for name, value in required_settings.items() if not value]
