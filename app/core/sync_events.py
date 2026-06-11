from datetime import datetime

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.sync import SyncOutbox
from app.services.sync_registry import entity_type_for_model, json_dumps, serialize_entity


def _session_sync_disabled(session: Session) -> bool:
    return bool(session.info.get("sync_disabled"))


def _apply_python_defaults(obj) -> None:
    now = datetime.utcnow()
    for attr in ("created_at", "updated_at", "captured_at", "analyzed_at"):
        if hasattr(obj, attr) and getattr(obj, attr) is None:
            setattr(obj, attr, now)

    for column in obj.__table__.columns:
        if column.name == "id" or getattr(obj, column.name) is not None or column.default is None:
            continue
        default = column.default.arg
        if callable(default):
            try:
                value = default()
            except TypeError:
                continue
        else:
            value = default
        setattr(obj, column.name, value)


@event.listens_for(Session, "before_flush")
def collect_sync_outbox_entries(session: Session, _flush_context, _instances) -> None:
    if _session_sync_disabled(session):
        return

    now = datetime.utcnow()
    pending: list[dict] = []

    for obj in session.new:
        if entity_type_for_model(obj) is None:
            continue
        _apply_python_defaults(obj)
        obj.sync_updated_at = now
        obj.sync_deleted_at = None
        pending.append(serialize_entity(obj, session, operation="upsert"))

    for obj in session.dirty:
        if entity_type_for_model(obj) is None or obj in session.deleted:
            continue
        if not session.is_modified(obj, include_collections=False):
            continue
        obj.sync_updated_at = now
        obj.sync_deleted_at = None
        pending.append(serialize_entity(obj, session, operation="upsert"))

    for obj in session.deleted:
        if entity_type_for_model(obj) is None:
            continue
        obj.sync_updated_at = now
        obj.sync_deleted_at = now
        pending.append(serialize_entity(obj, session, operation="delete"))

    if pending:
        session.info.setdefault("sync_pending_payloads", []).extend(pending)


@event.listens_for(Session, "after_flush")
def add_sync_outbox_entries(session: Session, _flush_context) -> None:
    if _session_sync_disabled(session):
        return

    pending = session.info.pop("sync_pending_payloads", [])
    for payload in pending:
        session.add(
            SyncOutbox(
                entity_type=payload["entity_type"],
                entity_sync_id=payload["sync_id"],
                operation=payload["operation"],
                payload_json=json_dumps(payload),
                status="pending",
            )
        )
