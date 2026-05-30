"""Manage LLM config ability — CRUD + mutual exclusion on activation."""

from __future__ import annotations

from backend.core.errors import NotFoundError, ValidationError
from backend.providers.admin_dtos import (
    LlmConfigItemDTO,
    LlmConfigListDTO,
    LlmConfigSaveDTO,
)
from backend.providers.env_file_provider import EnvFileProvider

VALID_PROVIDERS = frozenset({"openai", "anthropic", "deepseek", "custom"})


def list_llm_configs(env_file: EnvFileProvider) -> LlmConfigListDTO:
    return env_file.list_llm_configs()


def get_llm_config(env_file: EnvFileProvider, config_id: str) -> LlmConfigItemDTO:
    config = env_file.get_llm_config(config_id)
    if config is None:
        raise NotFoundError(f"LLM config '{config_id}' not found")
    return config


def create_llm_config(env_file: EnvFileProvider, dto: LlmConfigSaveDTO) -> LlmConfigItemDTO:
    if dto.provider not in VALID_PROVIDERS:
        raise ValidationError(
            f"Invalid provider '{dto.provider}'. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
        )
    return env_file.save_llm_config(dto)


def update_llm_config(
    env_file: EnvFileProvider,
    config_id: str,
    dto: LlmConfigSaveDTO,
) -> LlmConfigItemDTO:
    if dto.provider not in VALID_PROVIDERS:
        raise ValidationError(
            f"Invalid provider '{dto.provider}'. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
        )
    return env_file.save_llm_config(dto, config_id=config_id)


def delete_llm_config(env_file: EnvFileProvider, config_id: str) -> bool:
    return env_file.delete_llm_config(config_id)


def activate_llm_config(env_file: EnvFileProvider, config_id: str) -> LlmConfigItemDTO:
    config = env_file.activate_llm_config(config_id)
    if config is None:
        raise NotFoundError(f"LLM config '{config_id}' not found")
    return config
