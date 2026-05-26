from __future__ import annotations

import sentinel.agent.brain.cognition_loop as cognition_loop
import sentinel.agent.llm.memory_bridge as memory_bridge
import sentinel.agent.llm.memory_replay as memory_replay
import sentinel.agent.llm.memory_retrieval as memory_retrieval
import sentinel.agent.llm.memory_slots as memory_slots
import sentinel.agent.organs.proposal_bridge as proposal_bridge
import sentinel.organs.credentials.foundation as credential_foundation
from sentinel.shared.safety_scanner import (
    DOWNSTREAM_DANGEROUS_FORBIDDEN_KEYS,
    scan_forbidden_payload_flat,
)


VALIDATORS = [
    (cognition_loop, cognition_loop.validate_brain_cognition_payload),
    (memory_bridge, memory_bridge.validate_memory_payload),
    (memory_replay, memory_replay.validate_memory_replay_payload),
    (memory_retrieval, memory_retrieval.validate_memory_retrieval_payload),
    (memory_slots, memory_slots.validate_hot_context_slot_payload),
    (proposal_bridge, proposal_bridge.validate_organ_proposal_payload),
    (credential_foundation, credential_foundation.validate_authority_credential_payload),
]


def test_cognition_memory_and_credentials_use_one_shared_scanner() -> None:
    for module, validator in VALIDATORS:
        assert module.scan_forbidden_payload_flat is scan_forbidden_payload_flat
        safety = validator({"metadata": {"external_network": True, "provider_override": "auto"}})
        assert safety.valid is False
        assert "$.metadata.external_network" in safety.rejected_paths
        assert "$.metadata.provider_override" in safety.rejected_paths


def test_shared_scanner_covers_legacy_replay_and_credential_blockers() -> None:
    assert "revert_files" in DOWNSTREAM_DANGEROUS_FORBIDDEN_KEYS
    assert "credential_value" in DOWNSTREAM_DANGEROUS_FORBIDDEN_KEYS
    assert "secret_value" in DOWNSTREAM_DANGEROUS_FORBIDDEN_KEYS
    assert memory_replay.validate_memory_replay_payload({"revert_files": True}).valid is False
    assert credential_foundation.validate_authority_credential_payload({"credential_value": "present"}).valid is False
    assert credential_foundation.validate_authority_credential_payload({"secret_value": "present"}).valid is False


def test_shared_scanner_returns_safe_paths_without_echoing_secret_values() -> None:
    raw_secret = "Bearer " + "A" * 24
    for _, validator in VALIDATORS:
        safety = validator({"metadata": {"authorization": raw_secret}})
        assert safety.valid is False
        assert "$.metadata.authorization" in safety.rejected_paths
        assert raw_secret not in str(safety.rejected_paths)


def test_credential_secret_pattern_is_not_weakened_by_consolidation() -> None:
    short_legacy_key = "sk-" + "A" * 16
    safety = credential_foundation.validate_authority_credential_payload({"metadata": short_legacy_key})
    assert safety.valid is False
    assert "$.metadata" in safety.rejected_paths


def test_proposal_negative_control_descriptions_remain_data_not_execution() -> None:
    safety = proposal_bridge.validate_organ_proposal_payload(
        {"forbidden_substeps": ["browser_submit", "api_call", "credential"]}
    )
    assert safety.valid is True


def test_local_secret_patterns_are_replaced_by_shared_contract() -> None:
    for module, _ in VALIDATORS:
        assert not hasattr(module, "_SECRET_LIKE_PATTERN")
        assert not hasattr(module, "_SECRET_LIKE_TEXT")
