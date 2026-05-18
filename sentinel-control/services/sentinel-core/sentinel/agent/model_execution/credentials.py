from __future__ import annotations

import os
from enum import Enum

from pydantic import Field

from sentinel.agent.model_execution.models import ModelExecutionOutcomeClass
from sentinel.agent.model_execution.redaction import text_hash
from sentinel.shared.models import SentinelModel, new_id


class ProviderCredentialSource(str, Enum):
    ENV = "env"
    CREDENTIAL_REF = "credential_ref"


class ProviderCredentialHandle(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("provider_cred"))
    source_type: ProviderCredentialSource
    provider_id: str
    source_ref_hash: str
    scopes: list[str] = Field(default_factory=list)

    @classmethod
    def from_env(cls, *, provider_id: str, env_var_name: str, scopes: list[str]) -> ProviderCredentialHandle:
        return cls(
            source_type=ProviderCredentialSource.ENV,
            provider_id=provider_id,
            source_ref_hash=text_hash(env_var_name),
            scopes=sorted(set(scopes)),
        )


class CredentialResolution(SentinelModel):
    outcome_class: ModelExecutionOutcomeClass
    credential: ProviderCredentialHandle | None = None


class EnvironmentCredentialResolver:
    def __init__(self, provider_env: dict[str, dict[str, object]]) -> None:
        self._provider_env = provider_env

    def resolve(self, *, provider_id: str, required_scopes: list[str]) -> CredentialResolution:
        config = self._provider_env.get(provider_id)
        if config is None:
            return CredentialResolution(outcome_class=ModelExecutionOutcomeClass.MISSING_CREDENTIAL)
        env_var = config.get("env_var")
        if not isinstance(env_var, str) or not os.environ.get(env_var):
            return CredentialResolution(outcome_class=ModelExecutionOutcomeClass.MISSING_CREDENTIAL)
        scopes = config.get("scopes")
        scope_list = [str(scope) for scope in scopes] if isinstance(scopes, list) else required_scopes
        return CredentialResolution(
            outcome_class=ModelExecutionOutcomeClass.SUCCESS_VALIDATED,
            credential=ProviderCredentialHandle.from_env(provider_id=provider_id, env_var_name=env_var, scopes=scope_list),
        )
