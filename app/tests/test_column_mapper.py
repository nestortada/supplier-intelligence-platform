from app.utils.column_mapper import map_columns, normalize_column_name


def test_normalize_column_name_handles_spacing_and_symbols() -> None:
    assert normalize_column_name(" E-mail ") == "email"
    assert normalize_column_name("Distributor_Name") == "distributor name"
    assert normalize_column_name("Contact-Number") == "contact number"


def test_map_columns_detects_aliases() -> None:
    mapping = map_columns(["Distributor Name", "E-mail", "Contact Number", "Product Category"])

    assert mapping["company"] == "Distributor Name"
    assert mapping["email"] == "E-mail"
    assert mapping["phone"] == "Contact Number"
    assert mapping["category"] == "Product Category"
