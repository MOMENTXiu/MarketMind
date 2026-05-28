"""Issue auth tokens ability atom."""

from backend.providers.auth_dtos import AuthTokenClaimsDTO, AuthTokenPairDTO
from backend.providers.auth_token_provider import AuthTokenProvider


def issue_access_token(
    user_id: str,
    email: str,
    display_name: str | None,
    auth_token: AuthTokenProvider,
) -> str:
    claims = AuthTokenClaimsDTO(sub=user_id, email=email, display_name=display_name)
    return auth_token.sign_access_token(claims)


def issue_auth_token_pair(
    user_id: str,
    email: str,
    display_name: str | None,
    auth_token: AuthTokenProvider,
) -> AuthTokenPairDTO:
    access = issue_access_token(user_id, email, display_name, auth_token)
    return AuthTokenPairDTO(access_token=access, token_type="bearer")
