from datetime import datetime, timedelta
from decimal import Decimal

import httpx
import pytest

from app.models.amazon_data import AmazonProductData
from app.models.product import Product
from app.services.apify_service import (
    ApifyService,
    ApifyServiceError,
    build_apify_input,
    build_apify_tracking_input,
    map_apify_item_to_amazon_data,
)


def configure_apify_settings(monkeypatch) -> None:
    monkeypatch.setattr("app.services.apify_service.settings.APIFY_TOKEN", "token")
    monkeypatch.setattr("app.services.apify_service.settings.APIFY_ACTOR_ID", "detail-actor")
    monkeypatch.setattr("app.services.apify_service.settings.APIFY_TRACKING_ACTOR_ID", "tracking-actor")
    monkeypatch.setattr("app.services.apify_service.settings.APIFY_API_BASE_URL", "https://api.apify.test/v2")


def test_build_apify_input_uses_identifiers_and_fallback() -> None:
    product = Product(product_name="Widget", upc="111", ean="222", gtin="333")

    assert build_apify_input(product) == {
        "keywords": ["Widget"],
        "maxResultsPerKeyword": 50,
        "fullDetails": True,
        "marketplace": "com",
        "concurrency": 4,
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
        },
    }

    product.product_name = None
    product.upc = None
    assert build_apify_input(product)["keywords"] == ["222"]

    product.ean = None
    assert build_apify_input(product)["keywords"] == ["333"]

    # SKU is a valid URL
    product.sku = "https://www.amazon.com/example/dp/B0ABC12345/"
    apify_input = build_apify_input(product)
    assert apify_input["asins"] == ["B0ABC12345"]
    assert apify_input["startUrls"] == [{"url": "https://www.amazon.com/example/dp/B0ABC12345/"}]
    assert apify_input["fullDetails"] is True

    # SKU is a valid ASIN starting with B0
    product.sku = "B0BN72FYFG"
    apify_input = build_apify_input(product)
    assert apify_input["asins"] == ["B0BN72FYFG"]
    assert apify_input["startUrls"] == [{"url": "https://www.amazon.com/dp/B0BN72FYFG"}]

    # Adds latest ASIN from amazon_data as well if not already in identifiers
    product.amazon_data = [AmazonProductData(asin="B001ASINXX", captured_at=datetime.utcnow())]
    apify_input = build_apify_input(product)
    assert "B0BN72FYFG" in apify_input["asins"]
    assert "B001ASINXX" in apify_input["asins"]


def test_build_apify_tracking_input_uses_identifiers() -> None:
    product = Product(product_name="Widget", sku="B0BN72FYFG")

    assert build_apify_tracking_input(product) == {
        "identifiers": ["B0BN72FYFG"],
        "include_variants": False,
        "stream_output": True,
    }


def test_search_amazon_product_runs_both_actors_and_merges_results(monkeypatch) -> None:
    configure_apify_settings(monkeypatch)
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.method == "POST" and "/acts/detail-actor/runs" in str(request.url):
            return httpx.Response(201, json={"data": {"defaultDatasetId": "detail-dataset"}})
        if request.method == "POST" and "/acts/tracking-actor/runs" in str(request.url):
            return httpx.Response(201, json={"data": {"defaultDatasetId": "tracking-dataset"}})
        if "detail-dataset" in str(request.url):
            return httpx.Response(200, json=[{"asin": "B001", "title": "Amazon Widget", "estimated_monthly_sales": 1200}])
        return httpx.Response(200, json=[{"asin": "B001", "name": "Tracked Widget", "price_buybox": 11.99, "price_new_history": [10, 11, 12]}])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = ApifyService(client=client)

    result = service.search_amazon_product(Product(id=1, product_name="Widget", sku="B0BN72FYFG"))

    assert result is not None
    assert result["asin"] == "B001"
    assert result["title"] == "Amazon Widget"
    assert result["price_buybox"] == 11.99
    assert result["price_new_history"] == [10, 11, 12]
    assert result["apify_detail_actor_item"]["estimated_monthly_sales"] == 1200
    assert result["apify_tracking_actor_item"]["name"] == "Tracked Widget"
    assert "/acts/detail-actor/runs" in requests[0]
    assert "/datasets/detail-dataset/items" in requests[1]
    assert "/acts/tracking-actor/runs" in requests[2]
    assert "/datasets/tracking-dataset/items" in requests[3]


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

    result = service.run_actor({"keywords": ["Widget"]})

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


def test_map_apify_item_to_amazon_data_maps_sales_actor_fields() -> None:
    item = {
        "asin": "B0BZYCJK89",
        "url": "https://www.amazon.com/dp/B0BZYCJK89",
        "title": "Owala FreeSip Insulated Stainless Steel Water Bottle",
        "price": "$29.99",
        "list_price": "$34.99",
        "rating": 4.7,
        "review_count": 118592,
        "best_sellers_rank": [{"rank": 1, "category": "Kitchen & Dining"}],
        "bought_in_past_month": "20K+",
        "estimated_monthly_sales": 48953,
        "images": ["https://m.media-amazon.com/images/I/example.jpg"],
    }

    amazon_data = map_apify_item_to_amazon_data(10, item)

    assert amazon_data.asin == "B0BZYCJK89"
    assert amazon_data.amazon_url == "https://www.amazon.com/dp/B0BZYCJK89"
    assert amazon_data.amazon_title == "Owala FreeSip Insulated Stainless Steel Water Bottle"
    assert amazon_data.image_url == "https://m.media-amazon.com/images/I/example.jpg"
    assert amazon_data.current_price == Decimal("29.99")
    assert amazon_data.list_price == Decimal("34.99")
    assert amazon_data.rating == Decimal("4.7")
    assert amazon_data.reviews_count == 118592
    assert amazon_data.estimated_sales == 48953
    assert '"Kitchen & Dining"' in (amazon_data.sellers_history_json or "")
