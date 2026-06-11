import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import Numeric
from sqlalchemy.orm import Session

from app.models.amazon_data import AmazonProductData
from app.models.analysis import ProductAnalysis
from app.models.background_job import BackgroundJob
from app.models.email_campaign import EmailCampaign, EmailLog
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.user_profile import UserProfile


@dataclass(frozen=True)
class EntityConfig:
    entity_type: str
    collection: str
    model: type
    fk_fields: tuple[str, ...] = ()


ENTITY_CONFIGS: dict[str, EntityConfig] = {
    "user_profile": EntityConfig("user_profile", "profiles", UserProfile),
    "supplier": EntityConfig("supplier", "suppliers", Supplier, ("profile_id",)),
    "product": EntityConfig("product", "products", Product, ("profile_id", "supplier_id")),
    "amazon_product_data": EntityConfig("amazon_product_data", "amazon_product_data", AmazonProductData, ("product_id",)),
    "product_analysis": EntityConfig("product_analysis", "product_analyses", ProductAnalysis, ("product_id",)),
    "email_campaign": EntityConfig("email_campaign", "email_campaigns", EmailCampaign, ("profile_id",)),
    "email_log": EntityConfig("email_log", "email_logs", EmailLog, ("profile_id", "campaign_id", "supplier_id")),
    "background_job": EntityConfig("background_job", "background_jobs", BackgroundJob, ("profile_id",)),
}

SYNCABLE_MODELS = {config.model: config.entity_type for config in ENTITY_CONFIGS.values()}
INBOUND_ORDER = (
    "user_profile",
    "supplier",
    "product",
    "amazon_product_data",
    "product_analysis",
    "email_campaign",
    "email_log",
    "background_job",
)


def ensure_sync_identity(obj: Any, now: datetime | None = None) -> None:
    if getattr(obj, "sync_id", None) is None:
        obj.sync_id = uuid4().hex
    if getattr(obj, "sync_updated_at", None) is None:
        obj.sync_updated_at = now or datetime.utcnow()


def encode_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def decode_datetime(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        return parsed.replace(tzinfo=None)
    return None


def change_timestamp(payload: dict[str, Any]) -> datetime | None:
    deleted_at = decode_datetime(payload.get("sync_deleted_at"))
    updated_at = decode_datetime(payload.get("sync_updated_at"))
    if deleted_at and updated_at:
        return max(deleted_at, updated_at)
    return deleted_at or updated_at


def json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def json_loads(payload_json: str) -> dict[str, Any]:
    payload = json.loads(payload_json)
    return payload if isinstance(payload, dict) else {}


def entity_type_for_model(obj: Any) -> str | None:
    return SYNCABLE_MODELS.get(type(obj))


def _sync_id_for(session: Session, model: type, local_id: int | None) -> str | None:
    if local_id is None:
        return None
    related = session.get(model, local_id)
    if related is None:
        return None
    ensure_sync_identity(related)
    return related.sync_id


def _profile_sync_id_for_entity(entity_type: str, obj: Any, session: Session) -> str | None:
    if entity_type == "user_profile":
        return obj.sync_id
    profile = getattr(obj, "profile", None)
    if profile is not None:
        ensure_sync_identity(profile)
        return profile.sync_id
    if hasattr(obj, "profile_id"):
        return _sync_id_for(session, UserProfile, obj.profile_id)
    product = getattr(obj, "product", None)
    if product is not None:
        ensure_sync_identity(product)
        profile = getattr(product, "profile", None)
        if profile is not None:
            ensure_sync_identity(profile)
            return profile.sync_id
        return _sync_id_for(session, UserProfile, product.profile_id)
    if hasattr(obj, "product_id"):
        product = session.get(Product, obj.product_id)
        if product is not None:
            ensure_sync_identity(product)
            return _sync_id_for(session, UserProfile, product.profile_id)
    return None


def serialize_entity(obj: Any, session: Session, operation: str = "upsert") -> dict[str, Any]:
    entity_type = entity_type_for_model(obj)
    if entity_type is None:
        raise ValueError(f"Object is not syncable: {type(obj)!r}")

    ensure_sync_identity(obj)
    config = ENTITY_CONFIGS[entity_type]
    payload: dict[str, Any] = {
        "entity_type": entity_type,
        "operation": operation,
        "sync_id": obj.sync_id,
        "profile_sync_id": _profile_sync_id_for_entity(entity_type, obj, session),
    }

    for column in config.model.__table__.columns:
        if column.name == "id" or column.name in config.fk_fields:
            continue
        payload[column.name] = encode_value(getattr(obj, column.name))

    if entity_type == "product":
        supplier = getattr(obj, "supplier", None)
        if supplier is not None:
            ensure_sync_identity(supplier)
            payload["supplier_sync_id"] = supplier.sync_id
        else:
            payload["supplier_sync_id"] = _sync_id_for(session, Supplier, obj.supplier_id)
    elif entity_type in {"amazon_product_data", "product_analysis"}:
        product = getattr(obj, "product", None)
        if product is not None:
            ensure_sync_identity(product)
            payload["product_sync_id"] = product.sync_id
        else:
            payload["product_sync_id"] = _sync_id_for(session, Product, obj.product_id)
    elif entity_type == "email_log":
        campaign = getattr(obj, "campaign", None)
        supplier = getattr(obj, "supplier", None)
        if campaign is not None:
            ensure_sync_identity(campaign)
            payload["campaign_sync_id"] = campaign.sync_id
        else:
            payload["campaign_sync_id"] = _sync_id_for(session, EmailCampaign, obj.campaign_id)
        if supplier is not None:
            ensure_sync_identity(supplier)
            payload["supplier_sync_id"] = supplier.sync_id
        else:
            payload["supplier_sync_id"] = _sync_id_for(session, Supplier, obj.supplier_id)

    return payload


def local_change_timestamp(obj: Any) -> datetime | None:
    deleted_at = getattr(obj, "sync_deleted_at", None)
    updated_at = getattr(obj, "sync_updated_at", None)
    if deleted_at and updated_at:
        return max(deleted_at, updated_at)
    return deleted_at or updated_at


def find_local_by_sync_id(session: Session, entity_type: str, sync_id: str | None) -> Any | None:
    if not sync_id:
        return None
    config = ENTITY_CONFIGS[entity_type]
    return session.query(config.model).filter(config.model.sync_id == sync_id).first()


def _local_id_for_sync_id(session: Session, model: type, sync_id: str | None) -> int | None:
    if not sync_id:
        return None
    row = session.query(model).filter(model.sync_id == sync_id).first()
    return row.id if row is not None else None


def _assign_relationship_ids(session: Session, entity_type: str, obj: Any, payload: dict[str, Any]) -> bool:
    if hasattr(obj, "profile_id"):
        obj.profile_id = _local_id_for_sync_id(session, UserProfile, payload.get("profile_sync_id"))
        if obj.profile_id is None:
            return False
    if entity_type == "product":
        obj.supplier_id = _local_id_for_sync_id(session, Supplier, payload.get("supplier_sync_id"))
    elif entity_type in {"amazon_product_data", "product_analysis"}:
        obj.product_id = _local_id_for_sync_id(session, Product, payload.get("product_sync_id"))
        if obj.product_id is None:
            return False
    elif entity_type == "email_log":
        obj.campaign_id = _local_id_for_sync_id(session, EmailCampaign, payload.get("campaign_sync_id"))
        obj.supplier_id = _local_id_for_sync_id(session, Supplier, payload.get("supplier_sync_id"))
    return True


def _decode_column_value(column: Any, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(column.type, Numeric):
        return Decimal(str(value))
    if hasattr(column.type, "python_type"):
        try:
            if column.type.python_type is datetime:
                return decode_datetime(value)
        except NotImplementedError:
            return value
    return value


def apply_remote_payload(session: Session, entity_type: str, payload: dict[str, Any]) -> str:
    config = ENTITY_CONFIGS[entity_type]
    sync_id = payload.get("sync_id")
    if not sync_id:
        return "invalid"

    remote_time = change_timestamp(payload)
    obj = find_local_by_sync_id(session, entity_type, sync_id)
    if obj is not None:
        local_time = local_change_timestamp(obj)
        if local_time and remote_time and local_time > remote_time:
            return "local_newer"

    if payload.get("sync_deleted_at"):
        if obj is not None:
            session.delete(obj)
            return "deleted"
        return "missing_deleted"

    if obj is None:
        obj = config.model()
        obj.sync_id = sync_id
        session.add(obj)

    if not _assign_relationship_ids(session, entity_type, obj, payload):
        return "missing_dependency"

    for column in config.model.__table__.columns:
        if column.name == "id" or column.name in config.fk_fields:
            continue
        if column.name in payload:
            setattr(obj, column.name, _decode_column_value(column, payload[column.name]))

    return "applied"
