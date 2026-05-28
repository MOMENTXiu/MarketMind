"""Generic object storage provider interface."""

from __future__ import annotations

from typing import Protocol

from backend.providers.dtos import StoredObjectDTO


class ObjectStorageProvider(Protocol):
    """Narrow blob operations for S3-compatible object storage.

    Business-specific providers delegate to this interface through
    storage-specific adapters. Business code must not depend on this
    directly; it is an implementation detail of the adapter layer.
    """

    def put(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> StoredObjectDTO:
        """Store an object and return its metadata."""
        ...

    def get(self, key: str) -> bytes:
        """Read an object by key. Raise NotFoundError if absent."""
        ...

    def delete(self, key: str) -> bool:
        """Remove an object by key. Return True if it existed."""
        ...

    def stat(self, key: str) -> StoredObjectDTO | None:
        """Return metadata without reading payload."""
        ...

    def exists(self, key: str) -> bool:
        """Return True if the object exists."""
        ...

    def presigned_get_url(self, key: str, filename: str | None = None) -> str | None:
        """Return a short-lived presigned URL for direct download."""
        ...

    def list_keys(self, prefix: str) -> list[str]:
        """List object keys under a prefix."""
        ...
