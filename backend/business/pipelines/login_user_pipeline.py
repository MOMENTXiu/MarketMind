"""User login business pipeline."""

from backend.abilities.auth.authenticate_user import authenticate_user
from backend.abilities.auth.issue_auth_tokens import issue_auth_token_pair
from backend.providers.auth_dtos import AuthTokenPairDTO, UserIdentityDTO
from backend.providers.container import ProvidersContainer


class LoginUserPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def execute(self, email: str, password: str) -> tuple[UserIdentityDTO, AuthTokenPairDTO]:
        if (
            self.providers.user_directory is None
            or self.providers.password_hasher is None
            or self.providers.auth_token is None
        ):
            raise RuntimeError("Auth providers not configured")
        user = authenticate_user(
            email=email,
            password=password,
            user_directory=self.providers.user_directory,
            password_hasher=self.providers.password_hasher,
        )
        token_pair = issue_auth_token_pair(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            auth_token=self.providers.auth_token,
        )
        self.providers.user_directory.update_last_login(user.id)
        return user, token_pair
