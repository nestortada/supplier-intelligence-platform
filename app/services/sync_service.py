from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.sync import SyncOutbox, SyncState
from app.models.user_profile import UserProfile
from app.services.firestore_sync_client import FirestoreSyncClient
from app.services.sync_registry import (
    INBOUND_ORDER,
    apply_remote_payload,
    change_timestamp,
    decode_datetime,
    entity_type_for_model,
    ensure_sync_identity,
    json_dumps,
    json_loads,
    local_change_timestamp,
    serialize_entity,
)


class SyncClient(Protocol):
    def get_document(self, entity_type: str, profile_sync_id: str, sync_id: str) -> dict[str, Any] | None:
        ...

    def set_document(self, entity_type: str, profile_sync_id: str, sync_id: str, payload: dict[str, Any]) -> None:
        ...

    def iter_profiles(self) -> list[dict[str, Any]]:
        ...

    def iter_documents(self, entity_type: str, profile_sync_id: str) -> list[dict[str, Any]]:
        ...


def get_sync_client() -> SyncClient:
    return FirestoreSyncClient()


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _state_get(db: Session, key: str) -> str | None:
    state = db.get(SyncState, key)
    return state.value if state is not None else None


def _state_set(db: Session, key: str, value: str | None) -> None:
    state = db.get(SyncState, key)
    if state is None:
        db.add(SyncState(key=key, value=value))
    else:
        state.value = value
        state.updated_at = datetime.utcnow()


def enqueue_delete_tombstones(db: Session, objects: list[Any]) -> None:
    if db.info.get("sync_disabled"):
        return

    now = datetime.utcnow()
    now_iso = now.isoformat()
    with db.no_autoflush:
        for obj in objects:
            if entity_type_for_model(obj) is None:
                continue
            ensure_sync_identity(obj, now)
            payload = serialize_entity(obj, db, operation="delete")
            payload["sync_updated_at"] = now_iso
            payload["sync_deleted_at"] = now_iso
            db.add(
                SyncOutbox(
                    entity_type=payload["entity_type"],
                    entity_sync_id=payload["sync_id"],
                    operation="delete",
                    payload_json=json_dumps(payload),
                    status="pending",
                )
            )


class SyncService:
    def __init__(self, db: Session, client: SyncClient | None = None) -> None:
        self.db = db
        self.client = client

    def status(self) -> dict[str, Any]:
        pending_count = (
            self.db.query(func.count(SyncOutbox.id))
            .filter(SyncOutbox.status.in_(("pending", "failed")))
            .scalar()
            or 0
        )
        failed_count = self.db.query(func.count(SyncOutbox.id)).filter(SyncOutbox.status == "failed").scalar() or 0
        return {
            "enabled": settings.FIREBASE_ENABLED,
            "namespace": settings.FIREBASE_NAMESPACE,
            "last_successful_sync": _state_get(self.db, "last_successful_sync"),
            "last_inbound_sync": _state_get(self.db, "last_inbound_sync"),
            "last_error": _state_get(self.db, "last_error"),
            "pending_count": pending_count,
            "failed_count": failed_count,
        }

    def run_once(self) -> dict[str, Any]:
        if not settings.FIREBASE_ENABLED:
            return self.status()

        try:
            if self.client is None:
                self.client = get_sync_client()
            outbound = self._push_outbox()
            inbound = self._pull_remote()
            _state_set(self.db, "last_successful_sync", _now_iso())
            _state_set(self.db, "last_error", None)
            self.db.commit()
            result = self.status()
            result.update({"outbound": outbound, "inbound": inbound})
            return result
        except Exception as exc:
            self.db.rollback()
            _state_set(self.db, "last_error", str(exc))
            self.db.commit()
            result = self.status()
            result.update({"error": str(exc)})
            return result

    def _push_outbox(self) -> dict[str, int]:
        assert self.client is not None
        previous_sync_disabled = self.db.info.get("sync_disabled")
        self.db.info["sync_disabled"] = True
        pushed = 0
        remote_newer = 0
        failed = 0
        try:
            rows = (
                self.db.query(SyncOutbox)
                .filter(SyncOutbox.status.in_(("pending", "failed")))
                .order_by(SyncOutbox.created_at.asc(), SyncOutbox.id.asc())
                .limit(250)
                .all()
            )

            for row in rows:
                payload = json_loads(row.payload_json)
                profile_sync_id = payload.get("profile_sync_id") or payload.get("sync_id")
                if not profile_sync_id:
                    row.status = "failed"
                    row.attempts += 1
                    row.last_error = "Missing profile_sync_id."
                    failed += 1
                    continue

                try:
                    remote = self.client.get_document(row.entity_type, profile_sync_id, row.entity_sync_id)
                    remote_time = change_timestamp(remote or {})
                    local_time = change_timestamp(payload)
                    if remote and remote_time and local_time and remote_time > local_time:
                        self._apply_remote(row.entity_type, remote)
                        row.status = "skipped_remote_newer"
                        row.last_error = None
                        remote_newer += 1
                    else:
                        self.client.set_document(row.entity_type, profile_sync_id, row.entity_sync_id, payload)
                        row.status = "synced"
                        row.last_error = None
                        pushed += 1
                    row.updated_at = datetime.utcnow()
                except Exception as exc:
                    row.status = "failed"
                    row.attempts += 1
                    row.last_error = str(exc)
                    row.updated_at = datetime.utcnow()
                    failed += 1

            self.db.commit()
            return {"pushed": pushed, "remote_newer": remote_newer, "failed": failed}
        finally:
            if previous_sync_disabled is None:
                self.db.info.pop("sync_disabled", None)
            else:
                self.db.info["sync_disabled"] = previous_sync_disabled

    def _pull_remote(self) -> dict[str, int]:
        assert self.client is not None
        previous_sync_disabled = self.db.info.get("sync_disabled")
        self.db.info["sync_disabled"] = True
        applied = 0
        local_newer = 0
        skipped = 0
        try:
            last_inbound = decode_datetime(_state_get(self.db, "last_inbound_sync"))

            remote_profiles = self.client.iter_profiles()
            for payload in remote_profiles:
                if self._remote_payload_is_old(payload, last_inbound):
                    skipped += 1
                    continue
                result = self._apply_remote("user_profile", payload)
                if result in {"applied", "deleted"}:
                    applied += 1
                elif result == "local_newer":
                    local_newer += 1
                else:
                    skipped += 1

            self.db.commit()
            profile_sync_ids = {profile.sync_id for profile in self.db.query(UserProfile).all() if profile.sync_id}
            profile_sync_ids.update(payload.get("sync_id") for payload in remote_profiles if payload.get("sync_id"))

            for profile_sync_id in profile_sync_ids:
                for entity_type in INBOUND_ORDER:
                    if entity_type == "user_profile":
                        continue
                    for payload in self.client.iter_documents(entity_type, profile_sync_id):
                        if self._remote_payload_is_old(payload, last_inbound):
                            skipped += 1
                            continue
                        result = self._apply_remote(entity_type, payload)
                        if result in {"applied", "deleted"}:
                            applied += 1
                        elif result == "local_newer":
                            local_newer += 1
                        else:
                            skipped += 1
                self.db.commit()

            _state_set(self.db, "last_inbound_sync", _now_iso())
            return {"applied": applied, "local_newer": local_newer, "skipped": skipped}
        finally:
            if previous_sync_disabled is None:
                self.db.info.pop("sync_disabled", None)
            else:
                self.db.info["sync_disabled"] = previous_sync_disabled

    def _remote_payload_is_old(self, payload: dict[str, Any], last_inbound: datetime | None) -> bool:
        if last_inbound is None:
            return False
        remote_time = change_timestamp(payload)
        return bool(remote_time and remote_time < last_inbound)

    def _apply_remote(self, entity_type: str, payload: dict[str, Any]) -> str:
        previous = self.db.info.get("sync_disabled")
        self.db.info["sync_disabled"] = True
        try:
            return apply_remote_payload(self.db, entity_type, payload)
        finally:
            if previous is None:
                self.db.info.pop("sync_disabled", None)
            else:
                self.db.info["sync_disabled"] = previous
