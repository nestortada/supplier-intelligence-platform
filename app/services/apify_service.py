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


def build_apify_input(product: Product) -> dict[str, Any]:
    identifier = (
        product.upc
        or product.ean
        or product.gtin
        or _sku_search_identifier(product)
        or _latest_asin(product)
        or product.product_name
    )

    return {
        "identifiers": [identifier] if identifier else [],
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


def _json_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True, default=str)


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
        image_url=clean_text(data.get("image_url") or data.get("thumbnail_url")),
        current_price=_decimal_value(data.get("price") or data.get("current_price")),
        buybox_price=_decimal_value(data.get("price_buybox")),
        amazon_price=_decimal_value(data.get("price_amazon")),
        list_price=_decimal_value(data.get("list_price")),
        currency=clean_text(data.get("currency")),
        rating=_decimal_value(data.get("rating")),
        reviews_count=_int_value(data.get("n_reviews") or data.get("reviews_count")),
        sellers_count=_int_value(data.get("n_offers_new") or data.get("sellers_count")),
        estimated_sales=_int_value(data.get("estimated_sales") or data.get("monthly_sales") or data.get("sales")),
        price_history_json=_json_value(price_history),
        sellers_history_json=_json_value(data.get("n_offers_new_history")),
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

    def run_actor(self, input_data: dict) -> dict:
        missing_settings = self._missing_settings()
        if missing_settings:
            raise ApifyServiceError(f"Missing Apify settings: {', '.join(missing_settings)}")

        endpoint = f"{settings.APIFY_API_BASE_URL.rstrip('/')}/acts/{settings.APIFY_ACTOR_ID}/runs"
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
        if not input_data["identifiers"]:
            return None

        actor_run = self.run_actor(input_data)
        dataset_id = actor_run.get("defaultDatasetId")
        if not dataset_id:
            logger.warning("apify_run_missing_dataset", extra={"product_id": product.id})
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
    def _missing_settings(require_actor: bool = True) -> list[str]:
        required_settings = {
            "APIFY_TOKEN": settings.APIFY_TOKEN,
            "APIFY_API_BASE_URL": settings.APIFY_API_BASE_URL,
        }
        if require_actor:
            required_settings["APIFY_ACTOR_ID"] = settings.APIFY_ACTOR_ID
        return [name for name, value in required_settings.items() if not value]
