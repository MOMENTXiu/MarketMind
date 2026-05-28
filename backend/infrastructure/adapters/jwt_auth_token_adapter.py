"""JWT auth token adapter using python-jose."""

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from backend.core.errors import ExpiredTokenError, InfrastructureError, InvalidTokenError
from backend.providers.auth_dtos import AuthTokenClaimsDTO
from backend.providers.auth_token_provider import AuthTokenProvider


class JwtAuthTokenAdapter(AuthTokenProvider):
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,
        issuer: str | None = None,
        audience: str | None = None,
    ) -> None:
        self._secret = secret_key
        self._algorithm = algorithm
        self._expire_minutes = access_token_expire_minutes
        self._issuer = issuer
        self._audience = audience

    def sign_access_token(self, claims: AuthTokenClaimsDTO) -> str:
        now = datetime.now(UTC)
        exp = now + timedelta(minutes=self._expire_minutes)
        payload = {
            "sub": claims.sub,
            "email": claims.email,
            "display_name": claims.display_name,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        if self._issuer:
            payload["iss"] = self._issuer
        if self._audience:
            payload["aud"] = self._audience
        try:
            return jwt.encode(payload, self._secret, algorithm=self._algorithm)
        except Exception as exc:
            raise InfrastructureError(f"Token signing failed: {exc}") from exc

    def verify_access_token(self, token: str) -> AuthTokenClaimsDTO:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["sub", "exp"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredTokenError("Token has expired") from exc
        except JWTError as exc:
            raise InvalidTokenError(f"Invalid token: {exc}") from exc
        except Exception as exc:
            raise InvalidTokenError(f"Token verification failed: {exc}") from exc

        return AuthTokenClaimsDTO(
            sub=payload.get("sub", ""),
            email=payload.get("email", ""),
            display_name=payload.get("display_name"),
            iat=payload.get("iat"),
            exp=payload.get("exp"),
            iss=payload.get("iss"),
            aud=payload.get("aud"),
        )
