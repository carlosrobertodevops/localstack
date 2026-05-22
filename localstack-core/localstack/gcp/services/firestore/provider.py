from __future__ import annotations

import datetime
import uuid
from typing import Any

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.firestore.models import (
    FirestoreDatabase,
    FirestoreDataStore,
    FirestoreDocument,
)
from localstack.gcp.stores import GcpStores


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


class FirestoreProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = FirestoreDataStore()

    # databases
    def create_database(self, project: str, database_id: str = "(default)", *, location: str = "nam5") -> FirestoreDatabase:
        full = f"projects/{project}/databases/{database_id}"
        if full in self.data.databases:
            raise GcpAlreadyExists(f"database '{full}' already exists")
        self.resource_manager.ensure_project(project)
        db = FirestoreDatabase(name=full, location_id=location)
        self.data.databases[full] = db
        return db

    def get_database(self, project: str, database_id: str = "(default)") -> FirestoreDatabase:
        full = f"projects/{project}/databases/{database_id}"
        db = self.data.databases.get(full)
        if db is None:
            raise GcpNotFound(f"database '{full}' not found")
        return db

    def ensure_database(self, project: str, database_id: str = "(default)") -> FirestoreDatabase:
        try:
            return self.get_database(project, database_id)
        except GcpNotFound:
            return self.create_database(project, database_id)

    # documents
    def create_document(self, project: str, database_id: str, parent_path: str, document_id: str | None, fields: dict[str, Any]) -> FirestoreDocument:
        db = self.ensure_database(project, database_id)
        doc_id = document_id or uuid.uuid4().hex
        full = f"projects/{project}/databases/{database_id}/documents/{parent_path}/{doc_id}"
        if full in db.documents:
            raise GcpAlreadyExists(f"document '{full}' already exists")
        now = _now()
        doc = FirestoreDocument(name=full, fields=dict(fields), create_time=now, update_time=now)
        db.documents[full] = doc
        return doc

    def get_document(self, name: str) -> FirestoreDocument:
        project, database_id = _parse_document_name(name)
        db = self.get_database(project, database_id)
        doc = db.documents.get(name)
        if doc is None:
            raise GcpNotFound(f"document '{name}' not found")
        return doc

    def patch_document(self, name: str, fields: dict[str, Any]) -> FirestoreDocument:
        doc = self.get_document(name)
        doc.fields.update(fields)
        doc.update_time = _now()
        return doc

    def delete_document(self, name: str) -> None:
        project, database_id = _parse_document_name(name)
        db = self.get_database(project, database_id)
        if name not in db.documents:
            raise GcpNotFound(f"document '{name}' not found")
        del db.documents[name]

    def list_documents(self, project: str, database_id: str, parent_path: str) -> list[FirestoreDocument]:
        db = self.get_database(project, database_id)
        prefix = f"projects/{project}/databases/{database_id}/documents/{parent_path}/"
        return [d for d in db.documents.values() if d.name.startswith(prefix)]


def _parse_document_name(name: str) -> tuple[str, str]:
    parts = name.split("/")
    if len(parts) < 5 or parts[0] != "projects" or parts[2] != "databases":
        raise GcpInvalidRequest(f"invalid document name: {name}")
    return parts[1], parts[3]
