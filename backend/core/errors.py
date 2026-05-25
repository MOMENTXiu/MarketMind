"""Internal error types for provider and pipeline boundaries."""


class MarketMindError(Exception):
    """Base class for internal application errors."""


class ValidationError(MarketMindError):
    """Raised when internal business input fails validation."""


class NotFoundError(MarketMindError):
    """Raised when a requested domain resource cannot be found."""


class ProviderError(MarketMindError):
    """Raised when a provider capability fails."""


class InfrastructureError(MarketMindError):
    """Raised when infrastructure cannot complete an operation."""


class PipelineExecutionError(MarketMindError):
    """Raised when a business pipeline cannot complete."""


class BusinessFlowError(MarketMindError):
    """Raised when a business flow lifecycle cannot complete."""
