"""Sample file catalog and download API.

Sample metadata is served from an in-memory catalog. File bytes are streamed
from the configured object storage backend so the frontend never sees raw
bucket or object keys.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.dependencies import get_minio_storage, get_settings
from backend.core.errors import InfrastructureError, NotFoundError

router = APIRouter()

_SAMPLE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "order-sample",
        "name": "order_1.csv",
        "description": "Data-processing sample order dataset",
        "content_type": "text/csv",
        "storage_key": "samples/order-sample/order_1.csv",
    },
]


@router.get("/samples")
async def list_samples(
    settings: Any = Depends(get_settings),
) -> dict[str, Any]:
    samples = []
    for item in _SAMPLE_CATALOG:
        sample = dict(item)
        sample["download_url"] = f"/api/samples/{item['id']}/download"
        samples.append(sample)
    return {"samples": samples, "backend": settings.OBJECT_STORAGE_BACKEND}


@router.get("/samples/{sample_id}")
async def get_sample(sample_id: str) -> dict[str, Any]:
    for item in _SAMPLE_CATALOG:
        if item["id"] == sample_id:
            sample = dict(item)
            sample["download_url"] = f"/api/samples/{sample_id}/download"
            return sample
    raise HTTPException(status_code=404, detail="Sample not found")


@router.get("/samples/{sample_id}/download")
async def download_sample(
    sample_id: str,
    settings: Any = Depends(get_settings),
):
    item = None
    for s in _SAMPLE_CATALOG:
        if s["id"] == sample_id:
            item = s
            break
    if item is None:
        raise HTTPException(status_code=404, detail="Sample not found")

    if settings.OBJECT_STORAGE_BACKEND == "minio":
        storage = get_minio_storage(settings)
        try:
            data = storage.get(item["storage_key"])
        except NotFoundError:
            raise HTTPException(status_code=404, detail="Sample file not found in storage")
        except InfrastructureError as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        return StreamingResponse(
            iter([data]),
            media_type=item["content_type"],
            headers={
                "Content-Disposition": f'attachment; filename="{item["name"]}"',
            },
        )

    raise HTTPException(status_code=501, detail="Sample download not implemented for local backend")
