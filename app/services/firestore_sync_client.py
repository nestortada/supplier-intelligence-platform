from typing import Any

from app.core.config import settings
from app.services.sync_registry import ENTITY_CONFIGS


class FirestoreSyncClient:
    def __init__(self) -> None:
        if not settings.FIREBASE_ENABLED:
            raise RuntimeError("Firebase sync is disabled.")
        if not settings.FIREBASE_CREDENTIALS_PATH:
            raise RuntimeError("FIREBASE_CREDENTIALS_PATH is required when Firebase sync is enabled.")

        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
        except ImportError as exc:
            raise RuntimeError("firebase-admin is required when Firebase sync is enabled.") from exc

        app_name = "supplier-intelligence-sync"
        try:
            app = firebase_admin.get_app(app_name)
        except ValueError:
            credential = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            options = {"projectId": settings.FIREBASE_PROJECT_ID} if settings.FIREBASE_PROJECT_ID else None
            app = firebase_admin.initialize_app(credential, options=options, name=app_name)

        self._db = firestore.client(app)

    def _root_ref(self):
        return self._db.collection("supplier_intelligence").document(settings.FIREBASE_NAMESPACE)

    def _profile_ref(self, profile_sync_id: str):
        return self._root_ref().collection("profiles").document(profile_sync_id)

    def _document_ref(self, entity_type: str, profile_sync_id: str, sync_id: str):
        if entity_type == "user_profile":
            return self._profile_ref(sync_id)
        collection = ENTITY_CONFIGS[entity_type].collection
        return self._profile_ref(profile_sync_id).collection(collection).document(sync_id)

    def get_document(self, entity_type: str, profile_sync_id: str, sync_id: str) -> dict[str, Any] | None:
        snapshot = self._document_ref(entity_type, profile_sync_id, sync_id).get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        data.setdefault("sync_id", sync_id)
        data.setdefault("entity_type", entity_type)
        return data

    def set_document(self, entity_type: str, profile_sync_id: str, sync_id: str, payload: dict[str, Any]) -> None:
        self._document_ref(entity_type, profile_sync_id, sync_id).set(payload)

    def iter_profiles(self) -> list[dict[str, Any]]:
        profiles = []
        for snapshot in self._root_ref().collection("profiles").stream():
            data = snapshot.to_dict() or {}
            data.setdefault("sync_id", snapshot.id)
            data.setdefault("entity_type", "user_profile")
            profiles.append(data)
        return profiles

    def iter_documents(self, entity_type: str, profile_sync_id: str) -> list[dict[str, Any]]:
        collection = ENTITY_CONFIGS[entity_type].collection
        documents = []
        for snapshot in self._profile_ref(profile_sync_id).collection(collection).stream():
            data = snapshot.to_dict() or {}
            data.setdefault("sync_id", snapshot.id)
            data.setdefault("entity_type", entity_type)
            data.setdefault("profile_sync_id", profile_sync_id)
            documents.append(data)
        return documents
