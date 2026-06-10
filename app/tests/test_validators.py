from app.utils.validators import clean_price, clean_text, clean_upc, is_valid_email


def test_is_valid_email_accepts_valid_addresses() -> None:
    assert is_valid_email(" USER@example.com ")
    assert is_valid_email("sales.team+us@example.co")


def test_is_valid_email_rejects_invalid_addresses() -> None:
    assert not is_valid_email("not-an-email")
    assert not is_valid_email("user@example")
    assert not is_valid_email("")
    assert not is_valid_email(None)


def test_clean_text_converts_blank_values_to_none() -> None:
    assert clean_text("  value  ") == "value"
    assert clean_text("   ") is None
    assert clean_text(None) is None


def test_clean_upc_keeps_only_digits() -> None:
    assert clean_upc(" 012-345 678.0 ") == "0123456780"
    assert clean_upc("UPC: 12 34-56") == "123456"
    assert clean_upc("123456789012.0") == "123456789012"


def test_clean_upc_returns_none_for_empty_values() -> None:
    assert clean_upc("") is None
    assert clean_upc(None) is None
    assert clean_upc(float("nan")) is None


def test_clean_price_converts_common_formats() -> None:
    assert clean_price("$1,234.50") == 1234.5
    assert clean_price("1,234.50") == 1234.5
    assert clean_price("1234,50") == 1234.5
    assert clean_price(12.3) == 12.3


def test_clean_price_returns_none_for_blank_or_invalid_values() -> None:
    assert clean_price("") is None
    assert clean_price(None) is None
    assert clean_price("not available") is None
