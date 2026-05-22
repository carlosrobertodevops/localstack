from __future__ import annotations

import hashlib
from typing import Any

from localstack.gcp.exceptions import GcpAlreadyExists, GcpInvalidRequest, GcpNotFound
from localstack.gcp.resource_manager import ResourceManagerProvider
from localstack.gcp.services.storage.models import GcsBucket, GcsDataStore, GcsObject
from localstack.gcp.stores import GcpStores


class CloudStorageProvider:
    def __init__(
        self,
        *,
        resource_manager: ResourceManagerProvider | None = None,
        stores: GcpStores | None = None,
    ) -> None:
        self.stores = stores or GcpStores()
        self.resource_manager = resource_manager or ResourceManagerProvider(stores=self.stores)
        self.data = GcsDataStore()

    # --- buckets ---
    def create_bucket(self, project: str, name: str, *, location: str = "US", labels: dict[str, str] | None = None) -> GcsBucket:
        if not name:
            raise GcpInvalidRequest("bucket name required")
        if name in self.data.buckets:
            raise GcpAlreadyExists(f"bucket '{name}' already exists")
        self.resource_manager.ensure_project(project)
        bucket = GcsBucket(
            name=name,
            project=project,
            location=location,
            labels=dict(labels or {}),
            created=self.data.now_iso(),
        )
        self.data.buckets[name] = bucket
        return bucket

    def get_bucket(self, name: str) -> GcsBucket:
        bucket = self.data.buckets.get(name)
        if bucket is None:
            raise GcpNotFound(f"bucket '{name}' not found")
        return bucket

    def list_buckets(self, project: str | None = None) -> list[GcsBucket]:
        items = list(self.data.buckets.values())
        if project is not None:
            items = [b for b in items if b.project == project]
        return items

    def delete_bucket(self, name: str) -> None:
        if name not in self.data.buckets:
            raise GcpNotFound(f"bucket '{name}' not found")
        bucket = self.data.buckets[name]
        if bucket.objects:
            raise GcpInvalidRequest(f"bucket '{name}' is not empty")
        del self.data.buckets[name]

    # --- objects ---
    def put_object(self, bucket_name: str, object_name: str, content: bytes, *, content_type: str = "application/octet-stream", metadata: dict[str, str] | None = None) -> GcsObject:
        bucket = self.get_bucket(bucket_name)
        existing = bucket.objects.get(object_name)
        generation = (existing.generation + 1) if existing else 1
        etag = hashlib.md5(content, usedforsecurity=False).hexdigest()
        obj = GcsObject(
            name=object_name,
            bucket=bucket_name,
            content=content,
            content_type=content_type,
            metadata=dict(metadata or {}),
            generation=generation,
            size=len(content),
            updated=self.data.now_iso(),
            etag=etag,
        )
        bucket.objects[object_name] = obj
        return obj

    def get_object(self, bucket_name: str, object_name: str) -> GcsObject:
        bucket = self.get_bucket(bucket_name)
        obj = bucket.objects.get(object_name)
        if obj is None:
            raise GcpNotFound(f"object '{object_name}' not found in '{bucket_name}'")
        return obj

    def delete_object(self, bucket_name: str, object_name: str) -> None:
        bucket = self.get_bucket(bucket_name)
        if object_name not in bucket.objects:
            raise GcpNotFound(f"object '{object_name}' not found in '{bucket_name}'")
        del bucket.objects[object_name]

    def list_objects(self, bucket_name: str, *, prefix: str | None = None) -> list[GcsObject]:
        bucket = self.get_bucket(bucket_name)
        out = list(bucket.objects.values())
        if prefix is not None:
            out = [o for o in out if o.name.startswith(prefix)]
        return out

    def to_dict_bucket(self, bucket: GcsBucket) -> dict[str, Any]:
        return bucket.to_dict()

    def to_dict_object(self, obj: GcsObject) -> dict[str, Any]:
        return obj.to_dict()
