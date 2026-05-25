"""Map internal MarketMindError to FastAPI HTTPException at the controller boundary."""

from __future__ import annotations

from fastapi import HTTPException

from backend.core.errors import (
    BusinessFlowError,
    InfrastructureError,
    MarketMindError,
    NotFoundError,
    PipelineExecutionError,
    ProviderError,
    ValidationError,
)


def map_internal_error(exc: MarketMindError) -> HTTPException:
    """Translate an internal error into an HTTPException with stable detail."""

    detail = str(exc) or exc.__class__.__name__
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=detail)
    if isinstance(exc, ValidationError):
        return HTTPException(status_code=400, detail=detail)
    if isinstance(
        exc,
        (ProviderError, InfrastructureError, PipelineExecutionError, BusinessFlowError),
    ):
        return HTTPException(status_code=500, detail=detail)
    return HTTPException(status_code=500, detail=detail)
