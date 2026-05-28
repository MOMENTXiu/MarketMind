"""Tests for MinioObjectStorageAdapter using an in-memory fake."""

from __future__ import annotations

import pytest

from backend.core.errors import NotFoundError, ValidationError
from backend.providers.dtos import StoredObjectDTO
from backend.providers.object_storage_provider import ObjectStorageProvider


class _FakeObjectStorage:
    """In-memory fake for ObjectStorageProvider contract tests."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[bytes, str, dict[str, str]]] = {}

    def put(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> StoredObjectDTO:
        if not key or key.startswith("/") or ".." in key:
            raise ValidationError(f"Invalid object key: {key}")
        self._store[key] = (data, content_type, metadata or {})
        return StoredObjectDTO(
            storage_key=key,
            storage_uri=f"memory://{key}",
            content_type=content_type,
            size_bytes=len(data),
            checksum="fake-checksum",
            metadata=metadata or {},
        )

    def get(self, key: str) -> bytes:
        if key not in self._store:
            raise NotFoundError(f"Object not found: {key}")
        return self._store[key][0]

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def stat(self, key: str) -> StoredObjectDTO | None:
        if key not in self._store:
            return None
        data, content_type, metadata = self._store[key]
        return StoredObjectDTO(
            storage_key=key,
            storage_uri=f"memory://{key}",
            content_type=content_type,
            size_bytes=len(data),
            checksum="fake-checksum",
            metadata=metadata,
        )

    def exists(self, key: str) -> bool:
        return key in self._store

    def presigned_get_url(self, key: str, filename: str | None = None) -> str | None:
        return f"http://fake/{key}"

    def list_keys(self, prefix: str) -> list[str]:
        return [k for k in self._store if k.startswith(prefix)]


class TestObjectStorageProviderContract:
    """Contract tests against the ObjectStorageProvider Protocol."""

    @pytest.fixture
    def storage(self) -> ObjectStorageProvider:
        return _FakeObjectStorage()

    def test_put_and_get(self, storage: ObjectStorageProvider) -> None:
        stored = storage.put(
            "test/key.txt", b"hello", content_type="text/plain", metadata={"a": "1"}
        )
        assert stored.storage_key == "test/key.txt"
        assert stored.content_type == "text/plain"
        assert stored.size_bytes == 5
        assert stored.metadata == {"a": "1"}
        assert storage.get("test/key.txt") == b"hello"

    def test_get_missing_raises_not_found(self, storage: ObjectStorageProvider) -> None:
        with pytest.raises(NotFoundError):
            storage.get("missing/key")

    def test_stat_existing(self, storage: ObjectStorageProvider) -> None:
        storage.put("stat/key", b"data")
        stat = storage.stat("stat/key")
        assert stat is not None
        assert stat.size_bytes == 4

    def test_stat_missing_returns_none(self, storage: ObjectStorageProvider) -> None:
        assert storage.stat("missing/key") is None

    def test_exists(self, storage: ObjectStorageProvider) -> None:
        storage.put("exists/key", b"x")
        assert storage.exists("exists/key")
        assert not storage.exists("missing/key")

    def test_delete(self, storage: ObjectStorageProvider) -> None:
        storage.put("del/key", b"x")
        assert storage.delete("del/key")
        assert not storage.delete("del/key")

    def test_list_keys(self, storage: ObjectStorageProvider) -> None:
        storage.put("prefix/a.txt", b"1")
        storage.put("prefix/b.txt", b"2")
        storage.put("other/c.txt", b"3")
        keys = storage.list_keys("prefix/")
        assert sorted(keys) == ["prefix/a.txt", "prefix/b.txt"]

    def test_invalid_key_rejected(self, storage: ObjectStorageProvider) -> None:
        with pytest.raises(ValidationError):
            storage.put("../escape", b"bad")
        with pytest.raises(ValidationError):
            storage.put("/absolute", b"bad")
