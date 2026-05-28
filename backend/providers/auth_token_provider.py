"""Auth token provider interface for signing and verifying access tokens."""

from typing import Protocol

from backend.providers.auth_dtos import AuthTokenClaimsDTO


class AuthTokenProvider(Protocol):
    def sign_access_token(self, claims: AuthTokenClaimsDTO) -> str:
        """Sign an access token from claims and return the token string."""

    def verify_access_token(self, token: str) -> AuthTokenClaimsDTO:
        """Verify a token string and return the decoded claims.

        Raises:
            InvalidTokenError: when token is malformed or signature is invalid.
            ExpiredTokenError: when token has expired.
        """
