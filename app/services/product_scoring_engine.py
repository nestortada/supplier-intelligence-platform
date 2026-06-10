import json
import statistics
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from app.models.amazon_data import AmazonProductData
from app.models.product import Product


WEIGHTS = {
    "profitability": 0.30,
    "roi": 0.20,
    "sales": 0.20,
    "price_stability": 0.15,
    "sellers": 0.10,
    "data_quality": 0.05,
}

if round(sum(WEIGHTS.values()), 10) != 1.0:
    raise ValueError("Product scoring weights must sum to 1.0.")


DEFAULT_REFERRAL_FEE_RATE = Decimal("0.15")
DEFAULT_FBA_FEE = Decimal("4.50")
DEFAULT_SHIPPING_COST = Decimal("0.75")
DEFAULT_PREP_FEE = Decimal("0.50")
DEFAULT_OTHER_COSTS = Decimal("0.50")

PRICE_HISTORY_KEYS = ("price_new_history", "price_buybox_history", "price_amazon_history")
PRICE_CHANGE_PENALTY_THRESHOLD = 10
NULL_PRICE_HISTORY_RATE_THRESHOLD = Decimal("0.20")


class ProductScoringEngine:
    def __init__(
        self,
        referral_fee_rate: Decimal | float | str = DEFAULT_REFERRAL_FEE_RATE,
        fba_fee: Decimal | float | str = DEFAULT_FBA_FEE,
        shipping_cost: Decimal | float | str = DEFAULT_SHIPPING_COST,
        prep_fee: Decimal | float | str = DEFAULT_PREP_FEE,
        other_costs: Decimal | float | str = DEFAULT_OTHER_COSTS,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.referral_fee_rate = self._decimal_or_none(referral_fee_rate) or DEFAULT_REFERRAL_FEE_RATE
        self.fba_fee = self._decimal_or_none(fba_fee) or DEFAULT_FBA_FEE
        self.shipping_cost = self._decimal_or_none(shipping_cost) or DEFAULT_SHIPPING_COST
        self.prep_fee = self._decimal_or_none(prep_fee) or DEFAULT_PREP_FEE
        self.other_costs = self._decimal_or_none(other_costs) or DEFAULT_OTHER_COSTS
        self.weights = weights or WEIGHTS

    def analyze_product(self, product: Product, amazon_data: AmazonProductData | None) -> dict:
        supplier_cost = self._decimal_or_none(product.supplier_cost)
        amazon_price = self._amazon_price(amazon_data)
        sellers_count = amazon_data.sellers_count if amazon_data else None
        estimated_sales = amazon_data.estimated_sales if amazon_data else None

        history_values = self._price_history_values(amazon_data)
        price_metrics = self._price_history_metrics(history_values)
        price_stability_score = self.score_price_stability(price_metrics)
        sales_score = self.score_sales(estimated_sales)
        sellers_score = self.score_sellers(sellers_count)
        data_quality_score = self.score_data_quality(
            product=product,
            amazon_price=amazon_price,
            supplier_cost=supplier_cost,
            sellers_count=sellers_count,
            estimated_sales=estimated_sales,
            has_price_history=price_metrics["has_price_history"],
        )

        missing_financial_data = (
            supplier_cost is None
            or supplier_cost <= 0
            or amazon_price is None
            or amazon_price <= 0
        )

        referral_fee = None
        total_cost = None
        net_profit = None
        margin = None
        roi = None

        if missing_financial_data:
            profitability_score = 0
            roi_score = 0
        else:
            referral_fee = amazon_price * self.referral_fee_rate
            total_cost = supplier_cost + referral_fee + self.fba_fee + self.shipping_cost + self.prep_fee + self.other_costs
            net_profit = amazon_price - total_cost
            margin = net_profit / amazon_price
            roi = net_profit / supplier_cost
            profitability_score = self.score_profitability(net_profit, margin)
            roi_score = self.score_roi(roi)

        final_opportunity_score = round(
            (profitability_score * self.weights["profitability"])
            + (roi_score * self.weights["roi"])
            + (sales_score * self.weights["sales"])
            + (price_stability_score * self.weights["price_stability"])
            + (sellers_score * self.weights["sellers"])
            + (data_quality_score * self.weights["data_quality"]),
            2,
        )

        risks = self._risks(
            product=product,
            net_profit=net_profit,
            roi=roi,
            sellers_count=sellers_count,
            estimated_sales=estimated_sales,
            price_metrics=price_metrics,
        )
        recommendation_status = self._recommendation_status(
            missing_financial_data=missing_financial_data,
            data_quality_score=data_quality_score,
            final_score=final_opportunity_score,
            net_profit=net_profit,
        )
        recommendation_reason = self._recommendation_reason(
            status=recommendation_status,
            net_profit=net_profit,
            roi=roi,
            estimated_sales=estimated_sales,
            sellers_count=sellers_count,
        )

        return {
            "supplier_cost": self._number(supplier_cost),
            "amazon_price": self._number(amazon_price),
            "referral_fee": self._number(referral_fee),
            "fba_fee": self._number(self.fba_fee),
            "shipping_cost": self._number(self.shipping_cost),
            "prep_fee": self._number(self.prep_fee),
            "other_costs": self._number(self.other_costs),
            "total_cost": self._number(total_cost),
            "net_profit": self._number(net_profit),
            "margin": self._number(margin, places=4),
            "roi": self._number(roi, places=4),
            "profitability_score": profitability_score,
            "roi_score": roi_score,
            "sales_score": sales_score,
            "price_stability_score": price_stability_score,
            "sellers_score": sellers_score,
            "data_quality_score": data_quality_score,
            "final_opportunity_score": final_opportunity_score,
            "recommendation_status": recommendation_status,
            "recommendation_reason": recommendation_reason,
            "risks": risks,
            "price_history": [self._number(value) if value is not None else None for value in history_values],
            "price_history_metrics": price_metrics,
        }

    @staticmethod
    def score_profitability(net_profit: Decimal, margin: Decimal) -> int:
        if net_profit <= 0:
            return 0
        if margin >= Decimal("0.35"):
            return 100
        if margin >= Decimal("0.25"):
            return 85
        if margin >= Decimal("0.20"):
            return 70
        if margin >= Decimal("0.15"):
            return 55
        if margin >= Decimal("0.10"):
            return 35
        return 15

    @staticmethod
    def score_roi(roi: Decimal) -> int:
        if roi >= Decimal("0.60"):
            return 100
        if roi >= Decimal("0.45"):
            return 85
        if roi >= Decimal("0.30"):
            return 70
        if roi >= Decimal("0.20"):
            return 50
        if roi >= Decimal("0.10"):
            return 30
        return 10

    @staticmethod
    def score_sales(estimated_sales: int | None) -> int:
        if estimated_sales is None:
            return 40
        if estimated_sales >= 1000:
            return 100
        if estimated_sales >= 750:
            return 85
        if estimated_sales >= 500:
            return 70
        if estimated_sales >= 300:
            return 50
        if estimated_sales >= 100:
            return 25
        return 10

    @staticmethod
    def score_sellers(sellers_count: int | None) -> int:
        if sellers_count is None:
            return 40
        if sellers_count < 2:
            return 15
        if sellers_count == 2:
            return 50
        if sellers_count == 3:
            return 65
        if sellers_count == 4:
            return 75
        if sellers_count == 5:
            return 85
        if sellers_count <= 9:
            return 90
        if sellers_count <= 14:
            return 95
        return 100

    @staticmethod
    def score_data_quality(
        product: Product,
        amazon_price: Decimal | None,
        supplier_cost: Decimal | None,
        sellers_count: int | None,
        estimated_sales: int | None,
        has_price_history: bool,
    ) -> int:
        score = 0

        if product.upc or product.ean or product.gtin:
            score += 30
        if amazon_price is not None and amazon_price > 0:
            score += 20
        if supplier_cost is not None and supplier_cost > 0:
            score += 20
        if sellers_count is not None:
            score += 10
        if estimated_sales is not None:
            score += 10
        if has_price_history:
            score += 10

        return min(score, 100)

    @staticmethod
    def score_price_stability(price_metrics: dict[str, Any]) -> int:
        if not price_metrics["has_price_history"]:
            return 40

        coefficient_of_variation = Decimal(str(price_metrics["coefficient_of_variation"] or 0))
        if coefficient_of_variation <= Decimal("0.05"):
            score = 100
        elif coefficient_of_variation <= Decimal("0.10"):
            score = 80
        elif coefficient_of_variation <= Decimal("0.15"):
            score = 60
        elif coefficient_of_variation <= Decimal("0.25"):
            score = 35
        else:
            score = 15

        if Decimal(str(price_metrics["price_drop_30_days"] or 0)) > Decimal("0.15"):
            score -= 20
        if price_metrics["number_of_price_changes"] > PRICE_CHANGE_PENALTY_THRESHOLD:
            score -= 10
        if Decimal(str(price_metrics["null_price_rate"] or 0)) >= NULL_PRICE_HISTORY_RATE_THRESHOLD:
            score -= 10

        return max(score, 0)

    def _recommendation_status(
        self,
        missing_financial_data: bool,
        data_quality_score: int,
        final_score: float,
        net_profit: Decimal | None,
    ) -> str:
        if missing_financial_data or data_quality_score < 50:
            return "insufficient_data"
        if final_score >= 80 and net_profit is not None and net_profit > 0:
            return "buy"
        if final_score >= 60 and net_profit is not None and net_profit > 0:
            return "review"
        return "discard"

    def _recommendation_reason(
        self,
        status: str,
        net_profit: Decimal | None,
        roi: Decimal | None,
        estimated_sales: int | None,
        sellers_count: int | None,
    ) -> str:
        if status == "insufficient_data":
            return "Product has insufficient data for a reliable recommendation."

        if net_profit is not None and net_profit <= 0:
            return "Product should be discarded because net profit is negative after estimated Amazon fees."

        if status == "buy":
            roi_percent = self._percent(roi)
            if estimated_sales is not None and estimated_sales >= 500 and sellers_count is not None and sellers_count > 2:
                return (
                    f"Strong opportunity because ROI is {roi_percent}, estimated sales are above 500 units, "
                    "and seller count shows healthy marketplace competition."
                )
            return f"Strong opportunity because ROI is {roi_percent} and the combined opportunity score is high."

        if status == "review":
            if estimated_sales is None:
                return "Product requires review because profitability is positive but sales data is missing."
            return "Product requires review because profitability is positive but the opportunity score is not high enough to buy automatically."

        return "Product should be discarded because the opportunity score does not meet the minimum threshold."

    def _risks(
        self,
        product: Product,
        net_profit: Decimal | None,
        roi: Decimal | None,
        sellers_count: int | None,
        estimated_sales: int | None,
        price_metrics: dict[str, Any],
    ) -> list[str]:
        risks = []

        if estimated_sales is None:
            risks.append("Missing estimated sales.")
        if sellers_count is not None and sellers_count < 2:
            risks.append("Seller count is too low, possible restricted brand or monopolized listing.")
        if Decimal(str(price_metrics["price_drop_30_days"] or 0)) > Decimal("0.15"):
            risks.append("Price dropped more than 15% in the last 30 days.")
        if price_metrics["has_price_history"] and Decimal(str(price_metrics["coefficient_of_variation"] or 0)) > Decimal("0.15"):
            risks.append("Price history is unstable.")
        if not (product.upc or product.ean or product.gtin):
            risks.append("Missing UPC/EAN/GTIN.")
        if net_profit is not None and net_profit <= 0:
            risks.append("Negative net profit.")
        if roi is not None and roi < Decimal("0.20"):
            risks.append("Low ROI.")

        return risks

    def _price_history_metrics(self, history_values: list[Decimal | None]) -> dict[str, Any]:
        valid_values = [value for value in history_values if value is not None and value > 0]
        total_observations = len(history_values)
        null_count = total_observations - len(valid_values)

        if not valid_values:
            return {
                "has_price_history": False,
                "average_price": None,
                "min_price": None,
                "max_price": None,
                "standard_deviation": None,
                "coefficient_of_variation": None,
                "price_drop_30_days": None,
                "number_of_price_changes": 0,
                "null_price_count": null_count,
                "null_price_rate": self._number(Decimal(null_count) / Decimal(total_observations), places=4)
                if total_observations
                else 0,
            }

        average_price = sum(valid_values) / Decimal(len(valid_values))
        standard_deviation = Decimal(str(statistics.pstdev([float(value) for value in valid_values]))) if len(valid_values) > 1 else Decimal("0")
        coefficient_of_variation = standard_deviation / average_price if average_price > 0 else Decimal("0")

        reference_value = valid_values[-31] if len(valid_values) > 30 else valid_values[0]
        latest_value = valid_values[-1]
        price_drop_30_days = (reference_value - latest_value) / reference_value if reference_value > 0 and latest_value < reference_value else Decimal("0")
        number_of_price_changes = sum(1 for previous, current in zip(valid_values, valid_values[1:]) if previous != current)
        null_price_rate = Decimal(null_count) / Decimal(total_observations) if total_observations else Decimal("0")

        return {
            "has_price_history": True,
            "average_price": self._number(average_price),
            "min_price": self._number(min(valid_values)),
            "max_price": self._number(max(valid_values)),
            "standard_deviation": self._number(standard_deviation, places=4),
            "coefficient_of_variation": self._number(coefficient_of_variation, places=4),
            "price_drop_30_days": self._number(price_drop_30_days, places=4),
            "number_of_price_changes": number_of_price_changes,
            "null_price_count": null_count,
            "null_price_rate": self._number(null_price_rate, places=4),
        }

    def _price_history_values(self, amazon_data: AmazonProductData | None) -> list[Decimal | None]:
        if amazon_data is None:
            return []

        raw_data = self._json_loads(amazon_data.raw_response_json) or {}
        if isinstance(raw_data, dict):
            for key in PRICE_HISTORY_KEYS:
                values = self._parse_history(raw_data.get(key))
                if any(value is not None for value in values):
                    return values

        return self._parse_history(amazon_data.price_history_json)

    def _parse_history(self, value: Any) -> list[Decimal | None]:
        if value is None:
            return []

        if isinstance(value, str):
            loaded = self._json_loads(value)
            if loaded is not None:
                return self._parse_history(loaded)
            return [self._decimal_or_none(value)]

        if isinstance(value, dict):
            for key in ("price", "value", "current_price", "new", "buybox", "amazon"):
                if key in value:
                    return [self._decimal_or_none(value.get(key))]
            parsed_values = []
            for item in value.values():
                parsed_values.extend(self._parse_history(item))
            return parsed_values

        if isinstance(value, (list, tuple)):
            parsed_values = []
            for item in value:
                if item is None:
                    parsed_values.append(None)
                elif isinstance(item, (list, tuple)):
                    parsed_values.append(self._decimal_from_sequence(item))
                else:
                    parsed_values.extend(self._parse_history(item))
            return parsed_values

        return [self._decimal_or_none(value)]

    def _decimal_from_sequence(self, values: list | tuple) -> Decimal | None:
        for item in reversed(values):
            decimal_value = self._decimal_or_none(item)
            if decimal_value is not None:
                return decimal_value
        return None

    def _amazon_price(self, amazon_data: AmazonProductData | None) -> Decimal | None:
        if amazon_data is None:
            return None

        for value in (
            amazon_data.current_price,
            amazon_data.buybox_price,
            amazon_data.amazon_price,
            amazon_data.list_price,
        ):
            decimal_value = self._decimal_or_none(value)
            if decimal_value is not None and decimal_value > 0:
                return decimal_value
        return None

    @staticmethod
    def _json_loads(value: str | None) -> Any:
        if not value:
            return None
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return None

    @staticmethod
    def _decimal_or_none(value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        try:
            decimal_value = Decimal(str(value).replace(",", "").replace("$", "").strip())
        except (InvalidOperation, ValueError, AttributeError):
            return None
        if not decimal_value.is_finite():
            return None
        return decimal_value

    @staticmethod
    def _number(value: Decimal | None, places: int = 2) -> float | None:
        if value is None:
            return None
        quantize_value = Decimal("1") if places == 0 else Decimal("1." + ("0" * places))
        return float(value.quantize(quantize_value, rounding=ROUND_HALF_UP))

    @staticmethod
    def _percent(value: Decimal | None) -> str:
        if value is None:
            return "unknown"
        percent = (value * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"{percent}%"
