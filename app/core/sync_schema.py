from datetime import datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Engine


SYNC_TABLES = (
    "user_profiles",
    "suppliers",
    "products",
    "amazon_product_data",
    "product_analyses",
    "email_campaigns",
    "email_logs",
    "background_jobs",
)


def _table_columns(connection, table_name: str) -> set[str]:
    return {row[1] for row in connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()}


def ensure_sync_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    now = datetime.utcnow()
    with engine.begin() as connection:
        for table_name in SYNC_TABLES:
            columns = _table_columns(connection, table_name)
            if not columns:
                continue

            if "sync_id" not in columns:
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN sync_id VARCHAR(64)"))
            if "sync_updated_at" not in columns:
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN sync_updated_at DATETIME"))
            if "sync_deleted_at" not in columns:
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN sync_deleted_at DATETIME"))
            if table_name == "background_jobs" and "error_items_json" not in columns:
                connection.execute(text("ALTER TABLE background_jobs ADD COLUMN error_items_json TEXT"))

            rows = connection.execute(text(f"SELECT id FROM {table_name} WHERE sync_id IS NULL OR sync_id = ''")).fetchall()
            for row in rows:
                connection.execute(
                    text(f"UPDATE {table_name} SET sync_id = :sync_id WHERE id = :id"),
                    {"sync_id": uuid4().hex, "id": row[0]},
                )

            columns = _table_columns(connection, table_name)
            timestamp_source = "updated_at" if "updated_at" in columns else "created_at" if "created_at" in columns else None
            if timestamp_source:
                connection.execute(
                    text(
                        f"""
                        UPDATE {table_name}
                        SET sync_updated_at = COALESCE(sync_updated_at, {timestamp_source}, :now)
                        WHERE sync_updated_at IS NULL
                        """
                    ),
                    {"now": now},
                )
            else:
                connection.execute(
                    text(f"UPDATE {table_name} SET sync_updated_at = :now WHERE sync_updated_at IS NULL"),
                    {"now": now},
                )

            connection.execute(
                text(f"CREATE UNIQUE INDEX IF NOT EXISTS ix_{table_name}_sync_id_unique ON {table_name} (sync_id)")
            )
