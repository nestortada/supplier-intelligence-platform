from datetime import datetime, timedelta

import httpx
import pytest

from app.models.amazon_data import AmazonProductData
from app.models.product import Product
from app.services.apify_service import ApifyService, ApifyServiceError, build_apify_input, map_apify_item_to_amazon_data


def configure_apify_settings(monkeypatch) -> None:
    monkeypatch.setattr("app.services.apify_service.settings.APIFY_TOKEN", "token")
    monkeypatch.setattr("app.services.apify_service.settings.APIFY_ACTOR_ID", "actor")
    monkeypatch.setattr("app.services.apify_service.settings.APIFY_API_BASE_URL", "https://api.apify.test/v2")


def test_build_apify_input_uses_identifier_priority() -> None:
    product = Product(product_name="Widget", upc="111", ean="222", gtin="333")

    assert build_apify_input(product) == {
        "identifiers": ["111"],
        "include_variants": False,
        "stream_output": True,
    }

    product.upc = None
    assert build_apify_input(product)["identifiers"] == ["222"]

    product.ean = None
    assert build_apify_input(product)["identifiers"] == ["333"]


def test_build_apify_input_uses_amazon_sku_before_latest_asin() -> None:
    product = Product(product_name="Widget", sku="https://www.amazon.com/example/dp/B0ABC12345/")
    product.amazon_data = [AmazonProductData(asin="OLDASIN123", captured_at=datetime.utcnow())]

    assert build_apify_input(product)["identifiers"] == ["https://www.amazon.com/example/dp/B0ABC12345/"]

    product.sku = "B0BN72FYFG"

    assert build_apify_input(product)["identifiers"] == ["B0BN72FYFG"]


def test_build_apify_input_uses_latest_asin_before_name() -> None:
    product = Product(product_name="Widget")
    product.amazon_data = [
        AmazonProductData(asin="OLD", captured_at=datetime.utcnow() - timedelta(days=2)),
        AmazonProductData(asin="NEW", captured_at=datetime.utcnow()),
    ]

    assert build_apify_input(product)["identifiers"] == ["NEW"]


def test_search_amazon_product_runs_actor_and_reads_dataset(monkeypatch) -> None:
    configure_apify_settings(monkeypatch)
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.method == "POST":
            return httpx.Response(201, json={"data": {"defaultDatasetId": "dataset-1"}})
        return httpx.Response(200, json=[{"asin": "B001", "title": "Amazon Widget"}])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = ApifyService(client=client)

    result = service.search_amazon_product(Product(id=1, product_name="Widget"))

    assert result == {"asin": "B001", "title": "Amazon Widget"}
    assert "/acts/actor/runs" in requests[0]
    assert "/datasets/dataset-1/items" in requests[1]


def test_apify_service_retries_temporary_errors(monkeypatch) -> None:
    configure_apify_settings(monkeypatch)
    monkeypatch.setattr("app.services.apify_service.time.sleep", lambda _: None)
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.TimeoutException("timeout")
        return httpx.Response(201, json={"data": {"defaultDatasetId": "dataset-1"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = ApifyService(client=client, max_retries=1)

    result = service.run_actor({"identifiers": ["Widget"]})

    assert result["defaultDatasetId"] == "dataset-1"
    assert attempts["count"] == 2


def test_apify_service_raises_on_non_retryable_http_error(monkeypatch) -> None:
    configure_apify_settings(monkeypatch)

    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(400, text="bad request")))
    service = ApifyService(client=client)

    with pytest.raises(ApifyServiceError):
        service.run_actor({"identifiers": ["Widget"]})


def test_map_apify_item_to_amazon_data_maps_flexible_fields() -> None:
    item = {
        "asin": "B001",
        "name": "Amazon Widget",
        "product_url": "https://amazon.test/widget",
        "thumbnail_url": "https://amazon.test/image.jpg",
        "price": "$12.50",
        "price_buybox": "11.99",
        "price_amazon": "13.25",
        "list_price": "$15.00",
        "currency": "USD",
        "rating": "4.5",
        "n_reviews": "1,234",
        "n_offers_new": "7",
        "monthly_sales": "250",
        "price_new_history": [10, 11, 12],
        "n_offers_new_history": [5, 6, 7],
    }

    amazon_data = map_apify_item_to_amazon_data(10, item)

    assert amazon_data.product_id == 10
    assert amazon_data.asin == "B001"
    assert amazon_data.amazon_title == "Amazon Widget"
    assert amazon_data.current_price == 12.5
    assert amazon_data.reviews_count == 1234
    assert amazon_data.sellers_count == 7
    assert amazon_data.estimated_sales == 250
    assert amazon_data.price_history_json == "[10, 11, 12]"
    assert '"asin": "B001"' in amazon_data.raw_response_json
