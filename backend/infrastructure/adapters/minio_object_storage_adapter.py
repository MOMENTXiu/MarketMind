"""MinIO-backed implementation of ObjectStorageProvider.

S3-compatible object storage adapter. All SDK exceptions are converted to
internal error types so business layers never see MinIO specifics.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta

from backend.core.errors import InfrastructureError, NotFoundError, ValidationError
from backend.providers.dtos import StoredObjectDTO

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:  # pragma: no cover
    Minio = None  # type: ignore[misc,assignment]
    S3Error = Exception  # type: ignore[misc,assignment]


class MinioObjectStorageAdapter:
    """S3-compatible object storage using MinIO."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
        secure: bool = False,
        presigned_ttl_seconds: int = 900,
        public_endpoint: str | None = None,
    ) -> None:
        if Minio is None:
            raise InfrastructureError("minio package is required for MinIO backend")
        self.bucket = bucket
        self.presigned_ttl = presigned_ttl_seconds
        self.public_endpoint = public_endpoint or endpoint
        host = endpoint.replace("http://", "").replace("https://", "")
        self.client = Minio(
            host,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            secure=secure,
        )

    def put(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> StoredObjectDTO:
        self._validate_key(key)
        from io import BytesIO

        try:
            self.client.put_object(
                self.bucket,
                key,
                BytesIO(data),
                length=len(data),
                content_type=content_type,
                metadata=metadata or {},
            )
        except S3Error as exc:
            if exc.code == "NoSuchBucket":
                raise InfrastructureError(f"Bucket does not exist: {self.bucket}") from exc
            raise InfrastructureError(f"Failed to put object {key}") from exc
        except Exception as exc:
            raise InfrastructureError(f"Failed to put object {key}") from exc

        etag = hashlib.md5(data).hexdigest()
        return StoredObjectDTO(
            storage_key=key,
            storage_uri=f"s3://{self.bucket}/{key}",
            content_type=content_type,
            size_bytes=len(data),
            checksum=etag,
            etag=etag,
            metadata=metadata or {},
            url=self._proxy_url(key),
        )

    def get(self, key: str) -> bytes:
        self._validate_key(key)
        try:
            response = self.client.get_object(self.bucket, key)
            return response.read()
        except S3Error as exc:
            if exc.code in ("NoSuchKey", "NoSuchObject"):
                raise NotFoundError(f"Object not found: {key}") from exc
            raise InfrastructureError(f"Failed to get object {key}") from exc
        except Exception as exc:
            raise InfrastructureError(f"Failed to get object {key}") from exc

    def delete(self, key: str) -> bool:
        self._validate_key(key)
        try:
            self.client.remove_object(self.bucket, key)
            return True
        except S3Error as exc:
            if exc.code in ("NoSuchKey", "NoSuchObject"):
                return False
            raise InfrastructureError(f"Failed to delete object {key}") from exc
        except Exception as exc:
            raise InfrastructureError(f"Failed to delete object {key}") from exc

    def stat(self, key: str) -> StoredObjectDTO | None:
        self._validate_key(key)
        try:
            so = self.client.stat_object(self.bucket, key)
            return StoredObjectDTO(
                storage_key=key,
                storage_uri=f"s3://{self.bucket}/{key}",
                content_type=so.content_type or "application/octet-stream",
                size_bytes=so.size,
                checksum=so.etag.strip('"') if so.etag else None,
                etag=so.etag.strip('"') if so.etag else None,
                metadata=dict(so.metadata) if so.metadata else {},
                url=self._proxy_url(key),
            )
        except S3Error as exc:
            if exc.code in ("NoSuchKey", "NoSuchObject"):
                return None
            raise InfrastructureError(f"Failed to stat object {key}") from exc
        except Exception as exc:
            raise InfrastructureError(f"Failed to stat object {key}") from exc

    def exists(self, key: str) -> bool:
        return self.stat(key) is not None

    def presigned_get_url(self, key: str, filename: str | None = None) -> str | None:
        self._validate_key(key)
        try:
            disposition = f'attachment; filename="{filename}"' if filename else None
            return self.client.presigned_get_object(
                self.bucket,
                key,
                expires=timedelta(seconds=self.presigned_ttl),
                response_headers={"response-content-disposition": disposition}
                if disposition
                else None,
            )
        except Exception:
            return None

    def list_keys(self, prefix: str) -> list[str]:
        try:
            return [
                obj.object_name
                for obj in self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
                if obj.object_name
            ]
        except Exception as exc:
            raise InfrastructureError(f"Failed to list objects with prefix {prefix}") from exc

    def _validate_key(self, key: str) -> None:
        if not key or key.startswith("/") or ".." in key:
            raise ValidationError(f"Invalid object key: {key}")

    def _proxy_url(self, key: str) -> str:
        return f"/api/storage/proxy/{key}"
