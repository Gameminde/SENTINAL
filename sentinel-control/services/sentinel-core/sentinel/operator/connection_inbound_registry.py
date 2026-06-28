from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from sentinel.operator.connection_identity_registry import (
    ConnectionIdentityRegistry,
    build_default_connection_identity_registry,
)
from sentinel.operator.connection_inbound_models import (
    InboundConnectionSourceKind,
    InboundIntakePolicy,
    InboundIntakeResult,
    InboundObservationEnvelope,
    InboundPromptInjectionFinding,
    InboundQuarantineDecision,
    InboundQuarantineStatus,
    InboundReadOnlyEvidenceArtifact,
    InboundReadOnlyReceipt,
    InboundReadOnlyReceiptStatus,
    InboundReplayView,
    InboundSecretExposureFinding,
    artifact_hash,
    build_bounded_preview,
    build_prompt_injection_labels,
    build_secret_exposure_labels,
)
from sentinel.operator.connection_manifest_registry import (
    ConnectionManifestRegistry,
    build_default_connection_manifest_registry,
)
from sentinel.shared.models import SentinelModel


_SOURCE_KIND_TO_CONNECTION: dict[InboundConnectionSourceKind, str] = {
    InboundConnectionSourceKind.CHANNEL_INBOUND_MESSAGE: "channel_connector_runtime",
    InboundConnectionSourceKind.EMAIL_INBOUND_MESSAGE: "channel_connector_runtime",
    InboundConnectionSourceKind.WEBHOOK_PAYLOAD: "channel_connector_runtime",
    InboundConnectionSourceKind.BROWSER_READ_ONLY_SNAPSHOT: "browser_read_only_observation",
    InboundConnectionSourceKind.EXTERNAL_API_READ_ONLY_RESPONSE: "external_api_dry_run",
    InboundConnectionSourceKind.VOICE_TRANSCRIPT: "voice_runtime",
    InboundConnectionSourceKind.DESKTOP_OBSERVATION_SNAPSHOT: "desktop_sidecar_runtime",
    InboundConnectionSourceKind.OPERATOR_UPLOADED_ARTIFACT: "file_system_workspace_bridge_read_only",
}


class ConnectionInboundReadOnlyRegistry(SentinelModel):
    manifest_registry: ConnectionManifestRegistry = Field(default_factory=build_default_connection_manifest_registry)
    identity_registry: ConnectionIdentityRegistry = Field(default_factory=build_default_connection_identity_registry)
    policy: InboundIntakePolicy = Field(default_factory=InboundIntakePolicy)
    data_not_authority: bool = True
    authority_effect: str = "none"
    authority_granting: bool = False
    can_grant_authority: bool = False
    can_execute: bool = False
    can_send: bool = False
    can_write: bool = False
    registry_can_execute: bool = False

    @model_validator(mode="after")
    def _registry_is_not_runtime(self) -> "ConnectionInboundReadOnlyRegistry":
        if self.authority_granting or self.can_grant_authority:
            raise ValueError("inbound registry cannot grant authority")
        if self.can_execute or self.can_send or self.can_write or self.registry_can_execute:
            raise ValueError("inbound registry cannot execute, send, or write")
        return self

    def connection_for_source_kind(self, source_kind: InboundConnectionSourceKind) -> str:
        return _SOURCE_KIND_TO_CONNECTION[source_kind]

    def source_kind_for_connection(self, connection_id: str) -> InboundConnectionSourceKind | None:
        for source_kind, mapped_connection_id in _SOURCE_KIND_TO_CONNECTION.items():
            if mapped_connection_id == connection_id:
                return source_kind
        return None

    def accept_observation(self, envelope: InboundObservationEnvelope) -> InboundIntakeResult:
        source_kind = envelope.source.source_kind
        if source_kind not in self.policy.allowed_source_kinds:
            raise ValueError("inbound source kind is not allowed by policy")
        try:
            manifest = self.manifest_registry.get(envelope.source.connection_id)
        except KeyError as exc:
            raise KeyError(f"manifest missing for inbound connection `{envelope.source.connection_id}`") from exc
        expected_connection_id = self.connection_for_source_kind(source_kind)
        if expected_connection_id != envelope.source.connection_id:
            raise ValueError("inbound source kind does not match connection manifest")
        try:
            identity_boundary = self.identity_registry.get(envelope.source.connection_id)
        except KeyError as exc:
            raise KeyError(f"identity boundary missing for inbound connection `{envelope.source.connection_id}`") from exc

        content_hash = envelope.content_hash
        prompt_labels = build_prompt_injection_labels(envelope.content)
        secret_labels = build_secret_exposure_labels(envelope.content)
        preview, redaction_labels = build_bounded_preview(
            envelope.content,
            max_chars=self.policy.max_preview_chars,
        )

        prompt_finding_payload = {
            "labels": prompt_labels,
            "content_hash": content_hash,
        }
        prompt_finding = InboundPromptInjectionFinding(
            labels=prompt_labels,
            content_hash=content_hash,
            finding_hash=artifact_hash(prompt_finding_payload),
        )
        secret_finding_payload = {
            "labels": secret_labels,
            "content_hash": content_hash,
            "redaction_applied": bool(secret_labels),
        }
        secret_finding = InboundSecretExposureFinding(
            labels=secret_labels,
            content_hash=content_hash,
            redaction_applied=bool(secret_labels),
            finding_hash=artifact_hash(secret_finding_payload),
        )
        quarantine_payload: dict[str, Any] = {
            "observation_id": envelope.observation_id,
            "source_kind": source_kind.value,
            "connection_id": envelope.source.connection_id,
            "status": InboundQuarantineStatus.QUARANTINED.value,
            "content_hash": content_hash,
            "prompt_injection_labels": prompt_labels,
            "secret_exposure_labels": secret_labels,
        }
        quarantine = InboundQuarantineDecision(
            observation_id=envelope.observation_id,
            source_kind=source_kind,
            connection_id=envelope.source.connection_id,
            status=InboundQuarantineStatus.QUARANTINED,
            content_hash=content_hash,
            prompt_injection_labels=prompt_labels,
            secret_exposure_labels=secret_labels,
            decision_hash=artifact_hash(quarantine_payload),
        )
        evidence_payload: dict[str, Any] = {
            "observation_id": envelope.observation_id,
            "quarantine_ref": quarantine.quarantine_id,
            "source_kind": source_kind.value,
            "connection_id": envelope.source.connection_id,
            "manifest_hash": manifest.manifest_hash,
            "identity_boundary_hash": identity_boundary.safe_summary()["boundary_safe_hash"],
            "content_hash": content_hash,
            "preview_hash": artifact_hash({"bounded_preview": preview}),
            "attachment_count": envelope.attachment_count,
            "link_count": envelope.link_count,
            "prompt_injection_labels": prompt_labels,
            "secret_exposure_labels": secret_labels,
            "redaction_labels": redaction_labels,
        }
        evidence = InboundReadOnlyEvidenceArtifact(
            observation_id=envelope.observation_id,
            quarantine_ref=quarantine.quarantine_id,
            source_kind=source_kind,
            connection_id=envelope.source.connection_id,
            manifest_hash=manifest.manifest_hash,
            identity_boundary_hash=identity_boundary.safe_summary()["boundary_safe_hash"],
            content_hash=content_hash,
            bounded_preview=preview,
            preview_hash=evidence_payload["preview_hash"],
            attachment_count=envelope.attachment_count,
            link_count=envelope.link_count,
            prompt_injection_labels=prompt_labels,
            secret_exposure_labels=secret_labels,
            redaction_labels=redaction_labels,
            artifact_hash=artifact_hash(evidence_payload),
        )
        receipt_payload = {
            "observation_id": envelope.observation_id,
            "quarantine_ref": quarantine.quarantine_id,
            "evidence_ref": evidence.evidence_id,
            "connection_id": envelope.source.connection_id,
            "source_kind": source_kind.value,
            "status": InboundReadOnlyReceiptStatus.RECORDED.value,
            "content_hash": content_hash,
        }
        receipt = InboundReadOnlyReceipt(
            observation_id=envelope.observation_id,
            quarantine_ref=quarantine.quarantine_id,
            evidence_ref=evidence.evidence_id,
            connection_id=envelope.source.connection_id,
            source_kind=source_kind,
            status=InboundReadOnlyReceiptStatus.RECORDED,
            content_hash=content_hash,
            receipt_hash=artifact_hash(receipt_payload),
        )
        return InboundIntakeResult(
            source=envelope.source,
            policy=self.policy,
            prompt_injection_finding=prompt_finding,
            secret_exposure_finding=secret_finding,
            quarantine_decision=quarantine,
            evidence_artifact=evidence,
            receipt=receipt,
        )

    def build_replay_view(self, results: tuple[InboundIntakeResult, ...]) -> InboundReplayView:
        artifact_hashes: list[str] = []
        for result in results:
            artifact_hashes.extend(
                (
                    result.quarantine_decision.decision_hash,
                    result.evidence_artifact.artifact_hash,
                    result.receipt.receipt_hash,
                )
            )
        return InboundReplayView(
            observation_count=len(results),
            quarantine_count=len(results),
            evidence_count=len(results),
            receipt_count=len(results),
            artifact_hashes=tuple(artifact_hashes),
        )

    def export_safe_summaries(self, results: tuple[InboundIntakeResult, ...]) -> list[dict[str, Any]]:
        return [result.export_safe_summary() for result in results]


def build_default_connection_inbound_registry() -> ConnectionInboundReadOnlyRegistry:
    return ConnectionInboundReadOnlyRegistry()


__all__ = [
    "ConnectionInboundReadOnlyRegistry",
    "build_default_connection_inbound_registry",
]
