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


# ---------- Auth / User / Owner errors ----------


class AuthError(MarketMindError):
    """Base class for authentication and authorization errors."""


class DuplicateEmailError(AuthError):
    """Raised when registering with an email that already exists."""


class InvalidCredentialsError(AuthError):
    """Raised when login credentials do not match."""


class DisabledUserError(AuthError):
    """Raised when an authenticated user account is disabled."""


class InvalidTokenError(AuthError):
    """Raised when a token is malformed or signature is invalid."""


class ExpiredTokenError(AuthError):
    """Raised when a token has passed its expiration time."""


class RevokedSessionError(AuthError):
    """Raised when a refresh/session token has been revoked."""


class InvalidSseTicketError(AuthError):
    """Raised when an SSE ticket is invalid, consumed, expired, or mismatched."""


class OwnerMismatchError(AuthError):
    """Raised when a user attempts to access a resource owned by another user."""


class UnauthenticatedError(AuthError):
    """Raised when an operation requires authentication but none was provided."""
