from sqlalchemy import text
from sqlalchemy.engine import Engine


def ensure_product_selection_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(products)")).fetchall()}
        if not columns:
            return

        if "selected_for_sale" not in columns:
            connection.execute(text("ALTER TABLE products ADD COLUMN selected_for_sale BOOLEAN NOT NULL DEFAULT 0"))
        if "sale_performance" not in columns:
            connection.execute(text("ALTER TABLE products ADD COLUMN sale_performance VARCHAR(20)"))
        if "selected_at" not in columns:
            connection.execute(text("ALTER TABLE products ADD COLUMN selected_at DATETIME"))

        connection.execute(
            text(
                """
                UPDATE products
                SET selected_for_sale = 0
                WHERE selected_for_sale IS NULL
                """
            )
        )
