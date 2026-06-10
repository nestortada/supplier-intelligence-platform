import json
from decimal import Decimal

from app.models.amazon_data import AmazonProductData
from app.models.product import Product
from app.services.product_scoring_engine import ProductScoringEngine, WEIGHTS


def analyze(
    supplier_cost: str | None = "10.00",
    amazon_price: str | None = "25.00",
    sellers_count: int | None = 4,
    estimated_sales: int | None = 1000,
    price_history: list | None = None,
    upc: str | None = "123456789012",
) -> dict:
    product = Product(product_name="Widget", upc=upc, supplier_cost=Decimal(supplier_cost) if supplier_cost else None)
    amazon_data = None
    if amazon_price is not None:
        amazon_data = AmazonProductData(
            current_price=Decimal(amazon_price),
            sellers_count=sellers_count,
            estimated_sales=estimated_sales,
            raw_response_json=json.dumps({"price_new_history": price_history}) if price_history is not None else None,
        )

    return ProductScoringEngine().analyze_product(product, amazon_data)


def test_weights_sum_to_one() -> None:
    assert sum(WEIGHTS.values()) == 1.0


def test_profitability_score_thresholds() -> None:
    engine = ProductScoringEngine()

    assert engine.score_profitability(Decimal("-1"), Decimal("-0.10")) == 0
    assert engine.score_profitability(Decimal("1"), Decimal("0.35")) == 100
    assert engine.score_profitability(Decimal("1"), Decimal("0.25")) == 85
    assert engine.score_profitability(Decimal("1"), Decimal("0.20")) == 70
    assert engine.score_profitability(Decimal("1"), Decimal("0.15")) == 55
    assert engine.score_profitability(Decimal("1"), Decimal("0.10")) == 35
    assert engine.score_profitability(Decimal("1"), Decimal("0.09")) == 15


def test_roi_score_thresholds() -> None:
    engine = ProductScoringEngine()

    assert engine.score_roi(Decimal("0.60")) == 100
    assert engine.score_roi(Decimal("0.45")) == 85
    assert engine.score_roi(Decimal("0.30")) == 70
    assert engine.score_roi(Decimal("0.20")) == 50
    assert engine.score_roi(Decimal("0.10")) == 30
    assert engine.score_roi(Decimal("0.09")) == 10


def test_sellers_score_rewards_more_marketplace_sellers() -> None:
    engine = ProductScoringEngine()

    assert engine.score_sellers(None) == 40
    assert engine.score_sellers(1) == 15
    assert engine.score_sellers(2) == 50
    assert engine.score_sellers(3) == 65
    assert engine.score_sellers(4) == 75
    assert engine.score_sellers(5) == 85
    assert engine.score_sellers(9) == 90
    assert engine.score_sellers(14) == 95
    assert engine.score_sellers(15) == 100


def test_sales_score_is_flexible_around_500_units() -> None:
    engine = ProductScoringEngine()

    assert engine.score_sales(None) == 40
    assert engine.score_sales(1000) == 100
    assert engine.score_sales(750) == 85
    assert engine.score_sales(500) == 70
    assert engine.score_sales(300) == 50
    assert engine.score_sales(100) == 25
    assert engine.score_sales(99) == 10


def test_price_stability_score_handles_missing_stable_drop_and_unstable_history() -> None:
    missing_history = analyze(price_history=None)
    stable_history = analyze(price_history=[25, 25, 25, 25])
    dropped_history = analyze(price_history=[20] + [16] * 30)
    unstable_history = analyze(
        price_history=[10, None, 30, None, 10, None, 30, None, 10, None, 30, None, 10, None, 30, None, 10, None, 30, None, 10, None, 30]
    )

    assert missing_history["price_stability_score"] == 40
    assert stable_history["price_stability_score"] == 100
    assert dropped_history["price_stability_score"] == 80
    assert "Price dropped more than 15% in the last 30 days." in dropped_history["risks"]
    assert unstable_history["price_stability_score"] == 0
    assert "Price history is unstable." in unstable_history["risks"]


def test_final_score_and_buy_recommendation() -> None:
    result = analyze(price_history=[25, 25, 25, 25])

    assert result["net_profit"] == 5.0
    assert result["margin"] == 0.2
    assert result["roi"] == 0.5
    assert result["profitability_score"] == 70
    assert result["roi_score"] == 85
    assert result["sales_score"] == 100
    assert result["sellers_score"] == 75
    assert result["data_quality_score"] == 100
    assert result["final_opportunity_score"] == 85.5
    assert result["recommendation_status"] == "buy"


def test_recommendation_final_discards_negative_profit_and_flags_insufficient_data() -> None:
    negative = analyze(amazon_price="15.00", price_history=[15, 15, 15])
    missing_price = analyze(amazon_price=None)

    assert negative["net_profit"] < 0
    assert negative["recommendation_status"] == "discard"
    assert "Negative net profit." in negative["risks"]

    assert missing_price["net_profit"] is None
    assert missing_price["recommendation_status"] == "insufficient_data"
