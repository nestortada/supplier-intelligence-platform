from decimal import Decimal


def calculate_margin(price: Decimal, cost: Decimal) -> Decimal:
    if price == 0:
        return Decimal("0")
    return (price - cost) / price
