"""User registration business pipeline."""

from backend.abilities.auth.register_user import register_user
from backend.providers.auth_dtos import UserIdentityDTO, UserRegistrationInputDTO
from backend.providers.container import ProvidersContainer


class RegisterUserPipeline:
    def __init__(self, providers: ProvidersContainer) -> None:
        self.providers = providers

    def execute(self, input_dto: UserRegistrationInputDTO) -> UserIdentityDTO:
        if self.providers.user_directory is None or self.providers.password_hasher is None:
            raise RuntimeError("Auth providers not configured")
        return register_user(
            input_dto=input_dto,
            user_directory=self.providers.user_directory,
            password_hasher=self.providers.password_hasher,
        )
