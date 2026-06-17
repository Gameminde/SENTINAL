from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from pydantic import Field, model_validator

from sentinel.agent.llm.proposals import DelegatedActionLevel
from sentinel.agent.model_execution.redaction import sanitize_metadata, stable_hash, text_hash
from sentinel.agent.organs.low_risk_finalgate import LowRiskFinalGate, LowRiskFinalGateInput
from sentinel.agent.organs.proposal_bridge import OrganProposalKind
from sentinel.agent.organs.reversible_workspace_executor import (
    L3ReversibleWorkspaceExecutor,
    L3WorkspaceActionKind,
    L3WorkspaceAttemptStatus,
    L3WorkspaceRequest,
    L3WorkspaceResult,
    L3WorkspaceRollbackReceipt,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.perf.hot_cold.artifact_ref_store import ArtifactRefStore
from sentinel.shared.events import EventBus
from sentinel.shared.models import SentinelModel
from sentinel.shared.safety_scanner import (
    OrganSafetyScanCategory,
    SHARED_SECRET_LIKE_PATTERN,
    scan_forbidden_payload_categorized,
)


class MutationArtifactStateError(RuntimeError):
    """Raised when a mutation artifact cannot advance without violating policy."""


class MutationArtifactFormat(StrEnum):
    FULL_TEXT_REPLACEMENT = "full_text_replacement"
    UNIFIED_DIFF = "unified_diff"
    ANCHORED_REPLACEMENT = "anchored_replacement"


class MutationArtifactChannelConfig(SentinelModel):
    max_chunk_bytes: int = Field(default=8_192, ge=64, le=64 * 1024)
    max_artifact_bytes: int = Field(default=32_768, ge=64, le=10 * 1024 * 1024)
    max_chunks: int = Field(default=8, ge=1, le=64)

    @model_validator(mode="after")
    def _validate_limits(self) -> MutationArtifactChannelConfig:
        if self.max_chunk_bytes > self.max_artifact_bytes:
            raise ValueError("mutation_chunk_limit_exceeds_artifact_limit")
        return self


class MutationArtifactProposal(SentinelModel):
    schema_version: str = "sentinel_mutation_proposal_v1"
    intent_id: str | None = None
    mission_id: str
    run_id: str
    mutation_id: str
    workspace_ref: str
    target_paths: list[str]
    base_hashes: dict[str, str]
    mutation_format: MutationArtifactFormat
    purpose_summary: str = Field(min_length=1, max_length=512)
    evidence_refs: list[str] = Field(default_factory=list)
    expected_postcondition: str = Field(min_length=1, max_length=512)
    expected_artifact_hash: str | None = None

    @model_validator(mode="after")
    def _validate_metadata_only_proposal(self) -> MutationArtifactProposal:
        if self.schema_version != "sentinel_mutation_proposal_v1":
            raise ValueError("mutation_proposal_schema_version_mismatch")
        if len(self.target_paths) != 1:
            raise ValueError("mutation_v3_requires_exactly_one_target")
        target = _safe_target(self.target_paths[0])
        if set(self.base_hashes) != {target} or not self.base_hashes[target]:
            raise ValueError("mutation_base_hashes_must_match_target")
        if SHARED_SECRET_LIKE_PATTERN.search(self.purpose_summary) or SHARED_SECRET_LIKE_PATTERN.search(
            self.expected_postcondition
        ):
            raise ValueError("mutation_proposal_secret_like_metadata")
        self.target_paths = [target]
        self.base_hashes = {target: self.base_hashes[target]}
        return self

    @property
    def target_path(self) -> str:
        return self.target_paths[0]

    @property
    def base_hash(self) -> str:
        return self.base_hashes[self.target_path]

    def safe_record(self) -> dict[str, Any]:
        return sanitize_metadata(self.model_dump(mode="json"))


class MutationArtifactChunk(SentinelModel):
    schema_version: str = "sentinel_mutation_chunk_v1"
    intent_id: str | None = None
    mission_id: str
    run_id: str
    mutation_id: str
    artifact_type: MutationArtifactFormat
    target_path: str
    base_hash: str
    chunk_index: int = Field(ge=0)
    chunk_count: int = Field(ge=1)
    payload: str = Field(exclude=True, repr=False)
    payload_hash: str

    @model_validator(mode="after")
    def _validate_chunk(self) -> MutationArtifactChunk:
        if self.schema_version != "sentinel_mutation_chunk_v1":
            raise ValueError("mutation_chunk_schema_version_mismatch")
        self.target_path = _safe_target(self.target_path)
        if self.chunk_index >= self.chunk_count:
            raise ValueError("mutation_chunk_index_out_of_range")
        if text_hash(self.payload) != self.payload_hash:
            raise ValueError("mutation_chunk_payload_hash_mismatch")
        if SHARED_SECRET_LIKE_PATTERN.search(self.payload):
            raise ValueError("mutation_chunk_secret_like_payload")
        return self

    def safe_record(self) -> dict[str, Any]:
        return sanitize_metadata(
            {
                "schema_version": self.schema_version,
                "intent_id": self.intent_id,
                "mission_id": self.mission_id,
                "run_id": self.run_id,
                "mutation_id": self.mutation_id,
                "artifact_type": self.artifact_type.value,
                "target_path": self.target_path,
                "base_hash": self.base_hash,
                "chunk_index": self.chunk_index,
                "chunk_count": self.chunk_count,
                "payload_hash": self.payload_hash,
                "payload_bytes": len(self.payload.encode("utf-8")),
            }
        )


class MutationChunkReceipt(SentinelModel):
    mutation_id: str
    chunk_index: int
    chunk_count: int
    payload_hash: str
    payload_bytes: int
    payload_persisted: bool = False
    safe_summary: str = "Validated mutation artifact chunk accepted."


class MutationArtifactAssembly(SentinelModel):
    mutation_id: str
    mission_id: str
    run_id: str
    target_path: str
    base_hash: str
    artifact_type: MutationArtifactFormat
    artifact_ref: str
    artifact_hash: str
    chunk_hashes: list[str]
    chunk_count: int
    size_bytes: int
    validation_status: str = "validated"
    receipt_refs: list[str] = Field(default_factory=list)


class MutationApplicationResult(SentinelModel):
    mutation_id: str
    status: str
    artifact_ref: str
    artifact_hash: str
    target_path: str
    before_hash: str
    after_hash: str | None = None
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_refs: list[str] = Field(default_factory=list)
    rollback_receipt_ref: str | None = None
    safe_summary: str
    workspace_result: Any = Field(default=None, exclude=True, repr=False)


@dataclass
class _MutationState:
    proposal: MutationArtifactProposal
    chunks: dict[int, MutationArtifactChunk] = field(default_factory=dict)
    expected_chunk_count: int | None = None
    assembly: MutationArtifactAssembly | None = None
    application: MutationApplicationResult | None = None
    application_request: L3WorkspaceRequest | None = None
    rollback: L3WorkspaceRollbackReceipt | None = None
    events: list[dict[str, Any]] = field(default_factory=list)


class GovernedMutationArtifactChannel:
    """Validated mutation data plane over the existing reversible workspace path.

    This channel holds and validates mutation artifacts. It cannot create
    authority and requires a caller-supplied governed workspace request factory
    before it can ask the existing L3 executor to apply a complete artifact.
    """

    def __init__(
        self,
        *,
        kernel: MissionKernel,
        workspace_root: Path,
        mission_id: str,
        run_id: str,
        workspace_ref: str,
        workspace_request_factory: Callable[[str, str, str], L3WorkspaceRequest],
        config: MutationArtifactChannelConfig | None = None,
        workspace_executor: L3ReversibleWorkspaceExecutor | None = None,
        runtime_guard: Callable[[], str | None] | None = None,
    ) -> None:
        self.kernel = kernel
        self.workspace_root = Path(workspace_root).resolve()
        self.mission_id = mission_id
        self.run_id = run_id
        self.workspace_ref = workspace_ref
        self.config = config or MutationArtifactChannelConfig()
        self.workspace_request_factory = workspace_request_factory
        self.workspace_executor = workspace_executor or L3ReversibleWorkspaceExecutor()
        self.runtime_guard = runtime_guard
        artifact_root = self.kernel.store.mission_dir(mission_id, create=True) / "ma"
        self.artifact_store = ArtifactRefStore(artifact_root, event_bus=EventBus(mission_id))
        self._states: dict[str, _MutationState] = {}

    def begin(self, proposal: MutationArtifactProposal) -> MutationArtifactProposal:
        self._guard_active()
        if proposal.mission_id != self.mission_id:
            raise MutationArtifactStateError("mutation_mission_mismatch")
        if proposal.run_id != self.run_id:
            raise MutationArtifactStateError("mutation_run_mismatch")
        if proposal.workspace_ref != self.workspace_ref:
            raise MutationArtifactStateError("mutation_workspace_mismatch")
        if proposal.mutation_id in self._states:
            raise MutationArtifactStateError("mutation_duplicate")
        target = self._target_path(proposal.target_path)
        if not target.exists() or text_hash(target.read_text(encoding="utf-8")) != proposal.base_hash:
            raise MutationArtifactStateError("mutation_base_hash_mismatch")
        state = _MutationState(proposal=proposal)
        self._states[proposal.mutation_id] = state
        self._record(
            state,
            event_type="mutation_proposed",
            metadata={
                "proposal_hash": stable_hash(proposal.safe_record()),
                "target_path": proposal.target_path,
                "base_hash": proposal.base_hash,
                "mutation_format": proposal.mutation_format.value,
            },
        )
        return proposal

    def accept_chunk(self, chunk: MutationArtifactChunk) -> MutationChunkReceipt:
        self._guard_active()
        if chunk.mutation_id not in self._states and self._states:
            raise MutationArtifactStateError("mutation_id_mismatch")
        state = self._state(chunk.mutation_id)
        proposal = state.proposal
        if chunk.mission_id != self.mission_id:
            raise MutationArtifactStateError("mutation_mission_mismatch")
        if chunk.run_id != self.run_id:
            raise MutationArtifactStateError("mutation_run_mismatch")
        if chunk.mutation_id != proposal.mutation_id:
            raise MutationArtifactStateError("mutation_id_mismatch")
        if proposal.intent_id and chunk.intent_id != proposal.intent_id:
            raise MutationArtifactStateError("mutation_intent_id_mismatch")
        if chunk.target_path != proposal.target_path:
            raise MutationArtifactStateError("mutation_target_path_mismatch")
        if chunk.base_hash != proposal.base_hash:
            raise MutationArtifactStateError("mutation_base_hash_mismatch")
        if chunk.artifact_type is not proposal.mutation_format:
            raise MutationArtifactStateError("mutation_artifact_type_mismatch")
        if chunk.chunk_count > self.config.max_chunks:
            raise MutationArtifactStateError("mutation_chunk_count_exceeded")
        payload_bytes = len(chunk.payload.encode("utf-8"))
        if payload_bytes > self.config.max_chunk_bytes:
            raise MutationArtifactStateError("mutation_chunk_size_exceeded")
        if chunk.chunk_index in state.chunks:
            raise MutationArtifactStateError("mutation_chunk_duplicate")
        if chunk.chunk_index != len(state.chunks):
            raise MutationArtifactStateError("mutation_chunk_out_of_order")
        if state.expected_chunk_count is not None and state.expected_chunk_count != chunk.chunk_count:
            raise MutationArtifactStateError("mutation_chunk_count_changed")
        state.expected_chunk_count = chunk.chunk_count
        state.chunks[chunk.chunk_index] = chunk
        receipt = MutationChunkReceipt(
            mutation_id=chunk.mutation_id,
            chunk_index=chunk.chunk_index,
            chunk_count=chunk.chunk_count,
            payload_hash=chunk.payload_hash,
            payload_bytes=payload_bytes,
        )
        self._record(
            state,
            event_type="mutation_artifact_chunk_accepted",
            metadata=receipt.model_dump(mode="json"),
        )
        return receipt

    def accepted_chunk_indexes(self, mutation_id: str) -> list[int]:
        return sorted(self._state(mutation_id).chunks)

    def record_provider_interruption(self, mutation_id: str, *, safe_error_class: str) -> None:
        state = self._state(mutation_id)
        self._record(
            state,
            event_type="mutation_artifact_provider_interrupted",
            metadata={
                "safe_error_class": safe_error_class,
                "accepted_chunk_indexes": self.accepted_chunk_indexes(mutation_id),
            },
        )

    def record_terminal_discard(self, mutation_id: str, *, terminal_reason: str) -> None:
        state = self._state(mutation_id)
        self._record(
            state,
            event_type="mutation_artifact_model_response_discarded_after_terminal",
            metadata={
                "terminal_reason_hash": text_hash(terminal_reason),
                "accepted_chunk_indexes": self.accepted_chunk_indexes(mutation_id),
            },
        )

    def abandon(self, mutation_id: str, *, reason: str) -> None:
        state = self._state(mutation_id)
        if state.application is not None:
            raise MutationArtifactStateError("mutation_abandon_after_application_blocked")
        self._record(
            state,
            event_type="mutation_artifact_abandoned",
            metadata={
                "reason": reason,
                "accepted_chunk_indexes": self.accepted_chunk_indexes(mutation_id),
            },
        )
        del self._states[mutation_id]

    def assemble(self, mutation_id: str) -> MutationArtifactAssembly:
        self._guard_active()
        state = self._state(mutation_id)
        if state.assembly is not None:
            return state.assembly
        expected = state.expected_chunk_count
        if expected is None or sorted(state.chunks) != list(range(expected)):
            raise MutationArtifactStateError("mutation_chunks_incomplete")
        payload = "".join(state.chunks[index].payload for index in range(expected))
        payload_bytes = payload.encode("utf-8")
        if len(payload_bytes) > self.config.max_artifact_bytes:
            raise MutationArtifactStateError("mutation_artifact_size_exceeded")
        scan = scan_forbidden_payload_categorized(payload, path="$.assembled_payload")
        if scan[OrganSafetyScanCategory.SECRET.value] or scan[OrganSafetyScanCategory.UNSAFE_PAYLOAD.value]:
            raise MutationArtifactStateError("mutation_artifact_secret_like_payload")
        artifact_hash = text_hash(payload)
        if state.proposal.expected_artifact_hash and state.proposal.expected_artifact_hash != artifact_hash:
            raise MutationArtifactStateError("mutation_aggregate_hash_mismatch")
        self._validate_artifact_shape(state.proposal.mutation_format, payload)
        current = self._target_path(state.proposal.target_path).read_text(encoding="utf-8")
        if text_hash(current) != state.proposal.base_hash:
            raise MutationArtifactStateError("mutation_base_hash_mismatch")
        try:
            ref = self.artifact_store.put(payload_bytes, content_type="text", llm_exposable=True)
        except (UnicodeDecodeError, ValueError) as exc:
            raise MutationArtifactStateError("mutation_artifact_safety_validation_failed") from exc
        state.assembly = MutationArtifactAssembly(
            mutation_id=mutation_id,
            mission_id=self.mission_id,
            run_id=self.run_id,
            target_path=state.proposal.target_path,
            base_hash=state.proposal.base_hash,
            artifact_type=state.proposal.mutation_format,
            artifact_ref=ref.content_hash,
            artifact_hash=artifact_hash,
            chunk_hashes=[state.chunks[index].payload_hash for index in range(expected)],
            chunk_count=expected,
            size_bytes=len(payload_bytes),
            receipt_refs=[f"artifact:{ref.content_hash}"],
        )
        state.chunks.clear()
        self._record(
            state,
            event_type="mutation_artifact_assembly_completed",
            metadata=state.assembly.model_dump(mode="json"),
            receipt_refs=state.assembly.receipt_refs,
        )
        return state.assembly

    def apply(self, mutation_id: str) -> MutationApplicationResult:
        self._guard_active()
        state = self._state(mutation_id)
        if state.application is not None:
            return MutationApplicationResult(
                mutation_id=mutation_id,
                status="duplicate_apply_blocked",
                artifact_ref=state.application.artifact_ref,
                artifact_hash=state.application.artifact_hash,
                target_path=state.application.target_path,
                before_hash=state.application.before_hash,
                after_hash=state.application.after_hash,
                receipt_refs=state.application.receipt_refs,
                safe_summary="Duplicate mutation application blocked.",
            )
        if state.assembly is None:
            raise MutationArtifactStateError("mutation_artifact_not_assembled")
        if state.assembly.artifact_type is not MutationArtifactFormat.FULL_TEXT_REPLACEMENT:
            raise MutationArtifactStateError("mutation_format_not_executable_v1")
        payload = self.artifact_store.get(state.assembly.artifact_ref).decode("utf-8")
        if text_hash(payload) != state.assembly.artifact_hash:
            raise MutationArtifactStateError("mutation_aggregate_hash_mismatch")
        current = self._target_path(state.assembly.target_path).read_text(encoding="utf-8")
        if text_hash(current) != state.assembly.base_hash:
            raise MutationArtifactStateError("mutation_base_hash_mismatch")
        request = self.workspace_request_factory(state.assembly.target_path, payload, state.assembly.base_hash)
        if (
            request.mission_id != self.mission_id
            or request.action_kind is not L3WorkspaceActionKind.REPLACE_TEXT_FILE
            or request.target_relative_path != state.assembly.target_path
            or request.before_hash != state.assembly.base_hash
            or request.content != payload
        ):
            raise MutationArtifactStateError("mutation_workspace_request_mismatch")
        validation = self.workspace_executor.validate_request(request)
        if not validation.valid:
            state.application = MutationApplicationResult(
                mutation_id=mutation_id,
                status="dry_run_blocked",
                artifact_ref=state.assembly.artifact_ref,
                artifact_hash=state.assembly.artifact_hash,
                target_path=state.assembly.target_path,
                before_hash=state.assembly.base_hash,
                receipt_refs=[],
                safe_summary="Mutation dry-run validation blocked execution.",
            )
            self._record(
                state,
                event_type="mutation_dry_run_blocked",
                metadata={
                    "mutation_id": mutation_id,
                    "validation_reasons": validation.reasons,
                    "artifact_hash": state.assembly.artifact_hash,
                },
            )
            return state.application
        self._guard_active()
        state.application_request = request
        result = self.workspace_executor.execute(request)
        receipt = getattr(result, "receipt", None)
        receipt_refs = [receipt.receipt_id] if receipt is not None else []
        terminal_reason = self.active_block_reason()
        if terminal_reason and result.attempt_status is L3WorkspaceAttemptStatus.MUTATED:
            state.application = MutationApplicationResult(
                mutation_id=mutation_id,
                status="terminal_detected_after_apply",
                artifact_ref=state.assembly.artifact_ref,
                artifact_hash=state.assembly.artifact_hash,
                target_path=state.assembly.target_path,
                before_hash=state.assembly.base_hash,
                after_hash=result.after_hash,
                receipt_refs=receipt_refs,
                safe_summary="Terminal mission state detected after mutation; safety rollback required.",
                workspace_result=result,
            )
            rollback = self.rollback(mutation_id, reason="safety_restore")
            finalgate_refs = self._finalgate_refs(request=request, result=result, rollback_receipt=rollback)
            state.application = state.application.model_copy(
                update={
                    "status": "rolled_back_after_terminal",
                    "after_hash": rollback.restored_hash,
                    "receipt_refs": [*receipt_refs, rollback.rollback_receipt_id],
                    "finalgate_refs": finalgate_refs,
                    "rollback_receipt_ref": rollback.rollback_receipt_id,
                    "safe_summary": "Mutation was rolled back after terminal mission state was detected.",
                }
            )
            self._record(
                state,
                event_type="mutation_rolled_back_after_terminal",
                metadata={
                    "mutation_id": mutation_id,
                    "terminal_reason_hash": text_hash(terminal_reason),
                    "rollback_success": rollback.rollback_success,
                    "restored_hash": rollback.restored_hash,
                    "finalgate_refs": finalgate_refs,
                },
                receipt_refs=state.application.receipt_refs,
                finalgate_refs=state.application.finalgate_refs,
            )
            return state.application
        status = "applied" if result.attempt_status is L3WorkspaceAttemptStatus.MUTATED else "blocked"
        finalgate_refs = self._finalgate_refs(request=request, result=result)
        state.application = MutationApplicationResult(
            mutation_id=mutation_id,
            status=status,
            artifact_ref=state.assembly.artifact_ref,
            artifact_hash=state.assembly.artifact_hash,
            target_path=state.assembly.target_path,
            before_hash=state.assembly.base_hash,
            after_hash=result.after_hash,
            receipt_refs=receipt_refs,
            finalgate_refs=finalgate_refs,
            safe_summary=result.safe_summary,
            workspace_result=result,
        )
        self._record(
            state,
            event_type="mutation_applied" if status == "applied" else "mutation_apply_blocked",
            metadata=state.application.model_dump(mode="json"),
            receipt_refs=receipt_refs,
            finalgate_refs=finalgate_refs,
        )
        return state.application

    @staticmethod
    def _finalgate_refs(
        *,
        request: L3WorkspaceRequest,
        result: L3WorkspaceResult,
        rollback_receipt: L3WorkspaceRollbackReceipt | None = None,
    ) -> list[str]:
        lane = request.delegated_lane
        contract = request.contract
        finalgate = LowRiskFinalGate().certify(
            LowRiskFinalGateInput(
                mission_id=request.mission_id,
                expected_action_level=DelegatedActionLevel.L3,
                expected_organ_kind=OrganProposalKind.FILE_OPERATION,
                allowed_lane_id=getattr(lane, "lane_id", None),
                expected_gate_result_id=getattr(contract, "gate_result_id", None),
                receipt=result.receipt,
                rollback_receipt=rollback_receipt,
                known_evidence_refs=list(getattr(lane, "evidence_refs", []) or []),
                known_receipt_refs=list(getattr(lane, "receipt_refs", []) or []),
                budget_refs=["governed_mutation_artifact_channel"],
                rollback_required=True,
                current_time=request.current_time,
            )
        )
        if finalgate.decision.value.startswith("certified_"):
            return [finalgate.certificate.certificate_id]
        return []

    def rollback(self, mutation_id: str, *, reason: str) -> L3WorkspaceRollbackReceipt:
        state = self._state(mutation_id)
        if state.application is None or not isinstance(state.application.workspace_result, L3WorkspaceResult):
            raise MutationArtifactStateError("mutation_rollback_unavailable")
        if state.rollback is not None:
            return state.rollback
        state.rollback = self.workspace_executor.rollback(state.application.workspace_result, rollback_reason=reason)
        if state.application_request is not None:
            finalgate_refs = self._finalgate_refs(
                request=state.application_request,
                result=state.application.workspace_result,
                rollback_receipt=state.rollback,
            )
            state.application = state.application.model_copy(
                update={
                    "status": "rollback_completed" if state.rollback.rollback_success else "rollback_failed",
                    "after_hash": state.rollback.restored_hash,
                    "receipt_refs": [*state.application.receipt_refs, state.rollback.rollback_receipt_id],
                    "finalgate_refs": finalgate_refs,
                    "rollback_receipt_ref": state.rollback.rollback_receipt_id,
                    "safe_summary": state.rollback.safe_summary,
                }
            )
        self._record(
            state,
            event_type="mutation_rollback_performed",
            metadata={
                "mutation_id": mutation_id,
                "rollback_success": state.rollback.rollback_success,
                "restored_hash": state.rollback.restored_hash,
            },
            receipt_refs=[state.rollback.rollback_receipt_id],
            finalgate_refs=state.application.finalgate_refs if state.application is not None else [],
        )
        return state.rollback

    def application_result(self, mutation_id: str) -> MutationApplicationResult | None:
        return self._state(mutation_id).application

    def safe_event_records(self, mutation_id: str) -> list[dict[str, Any]]:
        return list(self._state(mutation_id).events)

    def _state(self, mutation_id: str) -> _MutationState:
        try:
            return self._states[mutation_id]
        except KeyError as exc:
            raise MutationArtifactStateError("mutation_not_started") from exc

    def _guard_active(self) -> None:
        reason = self.active_block_reason()
        if reason:
            raise MutationArtifactStateError(reason)

    def active_block_reason(self) -> str | None:
        if self.runtime_guard is not None:
            reason = self.runtime_guard()
            if reason:
                return reason
        return self.kernel.terminal_block_reason(self.mission_id)

    def _target_path(self, relative_path: str) -> Path:
        target = (self.workspace_root / _safe_target(relative_path)).resolve()
        try:
            target.relative_to(self.workspace_root)
        except ValueError as exc:
            raise MutationArtifactStateError("mutation_target_path_escape") from exc
        return target

    @staticmethod
    def _validate_artifact_shape(artifact_type: MutationArtifactFormat, payload: str) -> None:
        if artifact_type is MutationArtifactFormat.FULL_TEXT_REPLACEMENT:
            if "\x00" in payload:
                raise MutationArtifactStateError("mutation_artifact_malformed")
            return
        if artifact_type is MutationArtifactFormat.UNIFIED_DIFF:
            lines = payload.splitlines()
            if len(lines) < 3 or not lines[0].startswith("--- ") or not lines[1].startswith("+++ ") or not any(
                line.startswith("@@ ") for line in lines[2:]
            ):
                raise MutationArtifactStateError("mutation_artifact_malformed")
            return
        raise MutationArtifactStateError("mutation_artifact_malformed")

    def _record(
        self,
        state: _MutationState,
        *,
        event_type: str,
        metadata: dict[str, Any],
        receipt_refs: list[str] | None = None,
        finalgate_refs: list[str] | None = None,
    ) -> None:
        safe_metadata = sanitize_metadata(metadata)
        state.events.append(
            {
                "event_type": event_type,
                "metadata": safe_metadata,
                "receipt_refs": receipt_refs or [],
                "finalgate_refs": finalgate_refs or [],
            }
        )
        self.kernel.store.append_event(
            self.mission_id,
            event_type=event_type,
            safe_summary=f"Governed mutation artifact channel recorded {event_type}.",
            metadata=safe_metadata,
            receipt_refs=receipt_refs or [],
            finalgate_certificate_refs=finalgate_refs or [],
        )


def _safe_target(value: str) -> str:
    if not value or "\\" in value:
        raise ValueError("mutation_target_path_invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts or ":" in value:
        raise ValueError("mutation_target_path_invalid")
    return path.as_posix()


__all__ = [
    "GovernedMutationArtifactChannel",
    "MutationApplicationResult",
    "MutationArtifactAssembly",
    "MutationArtifactChannelConfig",
    "MutationArtifactChunk",
    "MutationArtifactFormat",
    "MutationArtifactProposal",
    "MutationArtifactStateError",
    "MutationChunkReceipt",
]
