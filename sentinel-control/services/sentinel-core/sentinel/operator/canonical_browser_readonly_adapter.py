from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlparse, urlunparse

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernelError, ActionResult
from sentinel.operator.browser_affordance_contracts import BROWSER_COGNITIVE_AFFORDANCE_ORDER
from sentinel.operator.browser_environment_state import BrowserEnvironmentStateBuilder
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.real_browser_control_runtime import (
    BOUNDED_URL_AUTHORITY_REF,
    DEFAULT_SESSION_REF,
    RealBrowserControlRuntime,
    RealBrowserEngine,
    RealBrowserEngineElement,
    RealBrowserEngineSnapshot,
    SENTINEL_CHROMIUM_BACKEND_ID,
)
from sentinel.operator.redaction import redact_operator_text, redact_operator_value
from sentinel.shared.models import new_id


READ_ONLY_BROWSER_OPERATIONS = frozenset(
    {
        "real_browser.observe",
        "real_browser.open",
        "real_browser.search",
        "real_browser.open_result",
        "real_browser.inspect_result",
        "real_browser.extract_evidence",
        "real_browser.verify_extraction",
        "real_browser.recover_session",
    }
)

MUTATING_BROWSER_OPERATIONS = frozenset(
    {
        "real_browser.click",
        "real_browser.type_text",
        "real_browser.select_option",
        "real_browser.submit_form",
        "real_browser.upload",
        "real_browser.download",
        "real_browser.login",
        "real_browser.payment",
        "real_browser.execute_script",
    }
)


@dataclass
class FakeBrowserReadOnlyBackend:
    allowed_origins: tuple[str, ...]
    page_title: str = "Fake Browser Page"
    evidence_cards: tuple[dict[str, Any], ...] = ()
    cancel_during_next_call: Any | None = None
    material_action_override: bool = False
    survivor_count: int = 0
    cleanup_failure: bool = False
    call_log: list[str] = field(default_factory=list)
    cleanup_count: int = 0
    lease_released: bool = False
    provider_calls: int = 0
    real_browser_runs: int = 0
    external_network_calls: int = 0

    def __post_init__(self) -> None:
        self.allowed_origins = tuple(dict.fromkeys(self.allowed_origins or ("example.test",)))
        self.current_origin = self.allowed_origins[0]
        self.lease_id_hash = stable_hash({"fake_browser_lease": self.allowed_origins})[:24]
        self.engine_identity_hash = stable_hash("fake_browser_readonly_engine")[:24]
        self.context_identity_hash = stable_hash({"fake_context": self.allowed_origins})[:24]
        self.page_identity_hash = stable_hash({"fake_page": self.current_origin, "title": self.page_title})[:24]

    def perform(self, *, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        self.call_log.append(operation)
        token = self.cancel_during_next_call
        if token is not None:
            self.cancel_during_next_call = None
            token.cancel("fake_browser_effect_cancelled")
        status = "observation_success" if operation == "real_browser.observe" else "read_only_action_success"
        typed_outcome = _typed_outcome(operation=operation, evidence_cards=self.evidence_cards)
        if operation == "real_browser.search" and not self.evidence_cards:
            status = "no_results_confirmed"
            typed_outcome = {
                "operation": operation,
                "search_materiality": "NO_RESULTS_CONFIRMED",
                "material_effect_observed": False,
                "evidence_delta": 0,
            }
        return {
            "operation": operation,
            "status": status,
            "origin": self.current_origin,
            "page_title": self.page_title,
            "page_state_hash": self.page_state_hash(operation=operation),
            "selected_backend_id": "fake_browser_readonly",
            "actual_backend_id": "fake_browser_readonly",
            "session_backend_kind": "fake_in_memory",
            "root_browser_lease_id_hash": self.lease_id_hash,
            "browser_engine_identity_hash": self.engine_identity_hash,
            "backend_context_identity_hash": self.context_identity_hash,
            "page_identity_hash": self.page_identity_hash,
            "typed_observation": typed_outcome,
            "evidence_cards": tuple(_safe_evidence_card(card) for card in self.evidence_cards[:12]),
            "evidence_delta": len(self.evidence_cards),
        }

    def page_state_hash(self, *, operation: str = "real_browser.observe") -> str:
        return stable_hash(
            {
                "origin": self.current_origin,
                "title": self.page_title,
                "operation": operation,
                "evidence": tuple(stable_hash(card) for card in self.evidence_cards[:12]),
            }
        )

    def snapshot(self, *, operation: str = "real_browser.observe") -> RealBrowserEngineSnapshot:
        elements = [
            RealBrowserEngineElement(
                ref="input:search",
                role="searchbox",
                name="Search public docs",
                text_preview="Search public docs",
            ),
            RealBrowserEngineElement(
                ref="link:official_doc",
                role="link",
                name=self.page_title,
                text_preview=self.page_title,
            ),
        ]
        for index, card in enumerate(self.evidence_cards[:8], start=1):
            elements.append(
                RealBrowserEngineElement(
                    ref=f"evidence:card_{index}",
                    role="article",
                    name=str(card.get("title") or card.get("kind") or "Evidence card"),
                    text_preview=str(card.get("summary") or card.get("title") or ""),
                )
            )
        return RealBrowserEngineSnapshot(
            page_title=self.page_title,
            state_hash=self.page_state_hash(operation=operation),
            elements=tuple(elements),
        )

    def cleanup(self) -> dict[str, Any]:
        self.cleanup_count += 1
        if self.cleanup_failure:
            raise ActionKernelError("browser_readonly_cleanup_failed")
        self.lease_released = self.survivor_count == 0
        return {
            "cleanup_count": self.cleanup_count,
            "lease_released": self.lease_released,
            "survivor_count": self.survivor_count,
            "cleanup_completed": self.lease_released,
        }


@dataclass
class PhysicalBrowserReadOnlyBackend:
    kernel: MissionKernel
    engine: RealBrowserEngine | None = None
    engine_factory: Callable[[], RealBrowserEngine] | None = None
    allowed_origins: tuple[str, ...] = ("sqlite.org",)
    selected_backend_id: str = SENTINEL_CHROMIUM_BACKEND_ID
    bounded_url_ref: str = BOUNDED_URL_AUTHORITY_REF
    session_ref: str = DEFAULT_SESSION_REF
    cleanup_failure: bool = False
    cleanup_count: int = 0
    lease_released: bool = False
    provider_calls: int = 0
    real_browser_runs: int = 0
    external_network_calls: int = 0

    def __post_init__(self) -> None:
        self._site_scopes = _public_read_only_site_scopes(self.allowed_origins or ("sqlite.org",))
        self.allowed_origins = tuple(
            dict.fromkeys(host for scope in self._site_scopes for host in scope.accepted_host_forms)
        )
        self.current_origin = self._site_scopes[0].canonical_site
        self._pending_target_url = "about:blank"
        self._last_authority_match: dict[str, Any] = {}

    def assert_ready(self, *, root_mission_id: str, authority: MissionAuthorityEnvelope) -> dict[str, Any]:
        engine = self._require_engine()
        bind_root_session_id = getattr(engine, "bind_root_session_id", None)
        if callable(bind_root_session_id):
            bind_root_session_id(root_mission_id)
        bind_authority = getattr(engine, "bind_authority", None)
        if callable(bind_authority):
            bind_authority(authority)
        return {
            "backend_kind": "physical",
            "selected_backend_id": self.selected_backend_id,
            "actual_backend_id": getattr(engine, "browser_backend_id", self.selected_backend_id),
            "session_backend_kind": _engine_session_backend_kind(engine),
            "initial_target": "about:blank",
            "network_navigation_during_readiness": False,
        }

    def prepare_open_target(self, params: dict[str, Any]) -> None:
        requested = str(params.get("url") or params.get("target_origin") or "").strip()
        if not requested:
            raise ActionKernelError("browser_open_target_missing")
        target = _parse_browser_target(requested)
        match = _match_public_read_only_site_scope(target=target, site_scopes=self._site_scopes)
        self._last_authority_match = match
        if not match["matched"]:
            raise ActionKernelError("browser_origin_transition_not_authorized")
        self.current_origin = str(match["matched_host_form"])
        self._pending_target_url = str(target["target_url"])
        if self.engine is not None:
            _set_engine_target_url(self.engine, self._pending_target_url)

    def execute_physical(self, *, envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
        authority = context.get("authority")
        if not isinstance(authority, MissionAuthorityEnvelope):
            raise ActionKernelError("physical_browser_authority_missing")
        root_mission_id = str(context.get("root_mission_id") or "").strip()
        if not root_mission_id:
            raise ActionKernelError("physical_browser_root_mission_missing")
        token = context.get("root_cancellation_token")
        if getattr(token, "cancelled", False):
            raise ActionKernelError("root_mission_cancelled_before_browser_dispatch")
        engine = self._require_engine()
        bind_root_session_id = getattr(engine, "bind_root_session_id", None)
        if callable(bind_root_session_id):
            bind_root_session_id(root_mission_id)
        _set_engine_target_url(engine, self._pending_target_url)
        runtime_context = dict(context)
        runtime_context.setdefault("adapter_id", "canonical_physical_browser_readonly_adapter")
        runtime_context.setdefault("root_browser_runtime_lease", self._root_lease_context(root_mission_id))
        runtime_context.setdefault("mission_workspace_manifest", self._mission_workspace_manifest(root_mission_id))
        runtime = RealBrowserControlRuntime(
            kernel=self.kernel,
            mission_id=root_mission_id,
            engine=engine,
            bounded_url_ref=self.bounded_url_ref,
            session_ref=self.session_ref,
            selected_backend_id=self.selected_backend_id,
            product_context=runtime_context,
        )
        result = runtime.execute(envelope, authority=authority, context=runtime_context)
        self.real_browser_runs += 1
        if getattr(token, "cancelled", False):
            raise ActionKernelError("root_mission_cancelled_during_browser_effect")
        return self._with_canonical_observation(result, operation=envelope.operation, runtime_context=runtime_context)

    def cleanup(self) -> dict[str, Any]:
        self.cleanup_count += 1
        if self.cleanup_failure:
            raise ActionKernelError("physical_browser_readonly_cleanup_failed")
        engine = self.engine
        if engine is not None:
            close = getattr(engine, "close", None)
            if callable(close):
                close()
        self.lease_released = True
        return {
            "cleanup_count": self.cleanup_count,
            "lease_released": self.lease_released,
            "survivor_count": 0,
            "cleanup_completed": True,
            "selected_backend_id": self.selected_backend_id,
            "actual_backend_id": getattr(engine, "browser_backend_id", self.selected_backend_id),
            "session_backend_kind": _engine_session_backend_kind(engine) if engine is not None else "not_constructed",
        }

    def _root_lease_context(self, root_mission_id: str) -> dict[str, Any]:
        engine = self._require_engine()
        root_hash = stable_hash(
            {
                "root_mission_id": root_mission_id,
                "backend": getattr(engine, "browser_backend_id", self.selected_backend_id),
                "session_backend_kind": _engine_session_backend_kind(engine),
            }
        )
        return {
            "status": "ACTIVE",
            "root_browser_lease_id_hash": root_hash,
            "lease_hash": root_hash,
            "browser_engine_identity_hash": stable_hash({"root_hash": root_hash, "backend": self.selected_backend_id}),
            "backend_context_identity_hash": stable_hash(
                {"root_hash": root_hash, "session_backend_kind": _engine_session_backend_kind(engine)}
            ),
            "data_not_authority": True,
            "can_execute": False,
        }

    def _mission_workspace_manifest(self, root_mission_id: str) -> dict[str, Any]:
        handle = {
            "kind": "browser_session",
            "safe_ref": self.session_ref,
            "handle_hash": stable_hash({"root_mission_id": root_mission_id, "session_ref": self.session_ref}),
            "backend": self.selected_backend_id,
        }
        manifest = {
            "manifest_id": f"mission_workspace:{stable_hash(root_mission_id)[:24]}",
            "handles": [handle],
            "data_not_authority": True,
            "can_execute": False,
        }
        manifest["manifest_hash"] = stable_hash(manifest)
        return manifest

    def _with_canonical_observation(
        self,
        result: ActionResult,
        *,
        operation: str,
        runtime_context: dict[str, Any],
    ) -> ActionResult:
        engine = self._require_engine()
        cards = dict(result.context_cards)
        backend_execution = cards.get("browser_backend_execution") if isinstance(cards.get("browser_backend_execution"), dict) else {}
        environment_state = cards.get("browser_environment_state") if isinstance(cards.get("browser_environment_state"), dict) else {}
        root_lease = runtime_context.get("root_browser_runtime_lease") if isinstance(runtime_context, dict) else {}
        if not isinstance(root_lease, dict):
            root_lease = {}
        evidence_refs = _physical_evidence_refs(
            operation=operation,
            result_refs=result.evidence_refs,
            environment_state=environment_state,
        )
        page_identity_hash = _physical_page_identity_hash(
            operation=operation,
            result=result,
            environment_state=environment_state,
            receipt_refs=result.receipt_refs,
        )
        safe_observation = {
            "backend_kind": "physical",
            "browser_operation": operation,
            "status": result.status,
            "root_browser_lease_id_hash": str(root_lease.get("root_browser_lease_id_hash") or root_lease.get("lease_hash") or ""),
            "browser_engine_identity_hash": str(root_lease.get("browser_engine_identity_hash") or ""),
            "backend_context_identity_hash": str(root_lease.get("backend_context_identity_hash") or ""),
            "page_identity_hash": page_identity_hash,
            "selected_backend_id": str(backend_execution.get("selected_backend_id") or self.selected_backend_id),
            "actual_backend_id": str(backend_execution.get("actual_backend_id") or getattr(engine, "browser_backend_id", "")),
            "session_backend_kind": str(backend_execution.get("session_backend_kind") or _engine_session_backend_kind(engine)),
            "browser_environment_state_hash": str(cards.get("browser_environment_state_hash") or stable_hash(environment_state)),
            "browser_evidence_refs": evidence_refs,
            "evidence_delta": len(evidence_refs),
            "readable_page_perception": bool(
                operation in {"real_browser.open", "real_browser.open_result", "real_browser.search", "real_browser.extract_evidence"}
                and evidence_refs
            ),
            "human_readable_public_evidence_count": len(evidence_refs),
            "internal_evidence_verification": _internal_evidence_verification_status(
                operation=operation,
                evidence_count=len(evidence_refs),
            ),
            "verified_evidence_available": bool(evidence_refs),
            "site_authority_match": redact_operator_value(self._last_authority_match),
            "data_not_authority": True,
            "can_execute": False,
        }
        physical_environment_state = self._physical_environment_state(
            operation=operation,
            result=result,
            environment_state=environment_state,
            backend_execution=backend_execution,
            safe_observation=safe_observation,
            runtime_context=runtime_context,
        )
        cards["browser_environment_state_source"] = environment_state
        cards["browser_environment_state"] = physical_environment_state
        cards["browser_environment_state_hash"] = stable_hash(physical_environment_state)
        cards.setdefault("browser_readonly_observation", safe_observation)
        cards.setdefault(
            "browser_terminal_receipt",
            {
                "receipt_id": result.receipt_refs[0] if result.receipt_refs else "",
                "operation": operation,
                "status": result.status,
                "selected_backend_id": safe_observation["selected_backend_id"],
                "actual_backend_id": safe_observation["actual_backend_id"],
                "session_backend_kind": safe_observation["session_backend_kind"],
                "site_authority_match": redact_operator_value(self._last_authority_match),
                "material_action": result.material_action,
                "fake_backend": False,
                "data_not_authority": True,
                "can_execute": False,
            },
        )
        terminal_receipt = cards.get("browser_terminal_receipt")
        if isinstance(terminal_receipt, dict):
            safe_observation["browser_terminal_receipt"] = terminal_receipt
        runtime_failure_fact = cards.get("runtime_failure_fact")
        if isinstance(runtime_failure_fact, dict):
            safe_observation["runtime_failure_fact"] = runtime_failure_fact
        body_failure_packet = cards.get("model_visible_body_failure_packet")
        if isinstance(body_failure_packet, dict):
            safe_observation["model_visible_body_failure_packet"] = body_failure_packet
        safe_observation["failure_code"] = str(result.failure_code or result.blocked_reason or "")
        cards["browser_readonly_observation"] = safe_observation
        cards["simulated_backend"] = False
        return result.model_copy(update={"context_cards": cards, "evidence_refs": evidence_refs})

    def _physical_environment_state(
        self,
        *,
        operation: str,
        result: ActionResult,
        environment_state: dict[str, Any],
        backend_execution: dict[str, Any],
        safe_observation: dict[str, Any],
        runtime_context: dict[str, Any],
    ) -> dict[str, Any]:
        engine = self._require_engine()
        page_state = environment_state.get("page_state") if isinstance(environment_state.get("page_state"), dict) else {}
        world_summary = environment_state.get("world_model_summary") if isinstance(environment_state.get("world_model_summary"), dict) else {}
        page_title = (
            page_state.get("title")
            or page_state.get("page_title")
            or world_summary.get("page_title")
            or "unknown"
        )
        page_state_hash = str(
            page_state.get("state_hash")
            or page_state.get("page_state_hash")
            or safe_observation.get("page_identity_hash")
            or result.result_hash
        )
        available_actions = tuple(str(item) for item in runtime_context.get("available_actions") or ())
        return {
            "schema_version": "canonical_browser_environment_state_v1",
            "source_contract": str(environment_state.get("schema_version") or "real_browser_environment_state"),
            "task": {
                "objective_hash": text_hash(str(runtime_context.get("mission_objective") or "")),
                "progress": "physical_browser_action_observed",
                "remaining_provider_decisions": int(runtime_context.get("remaining_provider_decisions") or 0),
                "remaining_material_actions": int(runtime_context.get("remaining_material_actions") or 0),
            },
            "browser": {
                "selected_backend_id": str(backend_execution.get("selected_backend_id") or self.selected_backend_id),
                "actual_backend_id": str(backend_execution.get("actual_backend_id") or getattr(engine, "browser_backend_id", "")),
                "session_backend_kind": str(backend_execution.get("session_backend_kind") or _engine_session_backend_kind(engine)),
                "session_lease_status": "ACTIVE",
                "real_browser_runs": self.real_browser_runs,
                "external_network_calls": self.external_network_calls,
            },
            "page": {
                "origin_hash": str(getattr(engine, "safe_url_origin_hash", "") or ""),
                "title": redact_operator_text(str(page_title)),
                "page_state_hash": page_state_hash,
                "page_type": str(page_state.get("page_kind_guess") or "unknown"),
                "readiness": "observed" if result.status == "completed" else result.status,
            },
            "affordance_graph": {
                "available": [item for item in available_actions if item.startswith("real_browser_control.")],
                "order": list(BROWSER_COGNITIVE_AFFORDANCE_ORDER),
                "source": "ExecutableCapabilityGraph.routes",
            },
            "focus": {"selected_ref_hash": "", "selection_kind": "unknown"},
            "execution_signals": {
                "last_action": operation,
                "status": result.status,
                "failure_class": str(result.failure_class or ""),
                "evidence_delta": len(result.evidence_refs),
                "site_authority_match": redact_operator_value(self._last_authority_match),
            },
            "memory": {
                "public_evidence": tuple(result.evidence_refs),
                "evidence_count": len(result.evidence_refs),
            },
            "evaluation": {
                "typed_observation": redact_operator_value(
                    safe_observation.get("typed_observation") if isinstance(safe_observation.get("typed_observation"), dict) else {}
                ),
                "unknowns": () if result.evidence_refs else ("evidence_missing",),
                "contradictions": (),
            },
            "demand_load_handles": {
                "source_environment_state_hash": stable_hash(environment_state),
                "runtime_context_hash": stable_hash(runtime_context),
            },
            "limits": {
                "max_affordances": 12,
                "max_evidence_cards": 12,
                "max_depth": 2,
                "raw_dom_exposed": False,
                "cookies_exposed": False,
                "tokens_exposed": False,
                "selectors_as_protocol": False,
            },
            "data_not_authority": True,
            "authority_effect": "none",
            "can_grant_authority": False,
            "can_execute": False,
        }

    def _require_engine(self) -> RealBrowserEngine:
        if self.engine is None:
            if self.engine_factory is None:
                raise ActionKernelError("physical_browser_engine_missing")
            self.engine = self.engine_factory()
            _set_engine_target_url(self.engine, self._pending_target_url)
        return self.engine


class CanonicalBrowserReadOnlyAdapter:
    def __init__(self, backend: FakeBrowserReadOnlyBackend | PhysicalBrowserReadOnlyBackend) -> None:
        self.backend = backend

    def execute(self, envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
        token = context.get("root_cancellation_token")
        if getattr(token, "cancelled", False):
            raise ActionKernelError("root_mission_cancelled_before_browser_dispatch")
        operation = str(envelope.operation)
        params = dict(envelope.params)
        if operation not in READ_ONLY_BROWSER_OPERATIONS:
            raise ActionKernelError("browser_readonly_operation_not_registered")
        self._validate_read_only_preconditions(operation=operation, params=params)
        execute_physical = getattr(self.backend, "execute_physical", None)
        if callable(execute_physical):
            return execute_physical(envelope=envelope, context=context)
        observation = self.backend.perform(operation=operation, params=params)
        if getattr(token, "cancelled", False):
            raise ActionKernelError("root_mission_cancelled_during_browser_effect")
        environment_state = compile_canonical_browser_environment_state(
            backend=self.backend,
            operation=operation,
            observation=observation,
            available_actions=tuple(context.get("available_actions") or ()),
            mission_objective=str(context.get("mission_objective") or ""),
            remaining_provider_decisions=int(context.get("remaining_provider_decisions") or 0),
            remaining_material_actions=int(context.get("remaining_material_actions") or 0),
        )
        receipt_id = new_id("fake_browser_readonly_receipt")
        evidence_refs = tuple(
            dict.fromkeys(
                [
                    f"browser_state:{observation['page_state_hash'][:24]}",
                    *(
                        f"browser_evidence:{stable_hash(card)[:24]}"
                        for card in observation.get("evidence_cards", ())
                    ),
                ]
            )
        )
        safe_observation = {
            "backend_kind": "fake",
            "browser_operation": operation,
            "status": observation["status"],
            "page_state_hash": observation["page_state_hash"],
            "page_identity_hash": observation["page_identity_hash"],
            "root_browser_lease_id_hash": observation["root_browser_lease_id_hash"],
            "browser_engine_identity_hash": observation["browser_engine_identity_hash"],
            "backend_context_identity_hash": observation["backend_context_identity_hash"],
            "typed_observation": observation["typed_observation"],
            "browser_evidence_refs": evidence_refs,
            "evidence_delta": observation["evidence_delta"],
            "readable_page_perception": bool(
                operation in {"real_browser.open", "real_browser.open_result", "real_browser.search", "real_browser.extract_evidence"}
                and observation["evidence_delta"]
            ),
            "human_readable_public_evidence_count": int(observation["evidence_delta"]),
            "internal_evidence_verification": _internal_evidence_verification_status(
                operation=operation,
                evidence_count=int(observation["evidence_delta"]),
            ),
            "verified_evidence_available": bool(observation["evidence_delta"]),
            "browser_environment_state_hash": stable_hash(environment_state),
            "data_not_authority": True,
            "can_execute": False,
        }
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=operation,
            status="completed",
            receipt_refs=(receipt_id,),
            evidence_refs=evidence_refs,
            material_action=bool(self.backend.material_action_override),
            observation_summary=f"canonical browser read-only {operation} completed.",
            context_cards={
                "browser_readonly_observation": safe_observation,
                "browser_environment_state": environment_state,
                "browser_terminal_receipt": {
                    "receipt_id": receipt_id,
                    "operation": operation,
                    "status": observation["status"],
                    "root_browser_lease_id_hash": observation["root_browser_lease_id_hash"],
                    "backend_context_identity_hash": observation["backend_context_identity_hash"],
                    "page_identity_hash": observation["page_identity_hash"],
                    "selected_backend_id": observation["selected_backend_id"],
                    "actual_backend_id": observation["actual_backend_id"],
                    "session_backend_kind": observation["session_backend_kind"],
                    "material_action": bool(self.backend.material_action_override),
                    "fake_backend": True,
                    "data_not_authority": True,
                    "can_execute": False,
                },
                "simulated_backend": True,
            },
        )

    def _validate_read_only_preconditions(self, *, operation: str, params: dict[str, Any]) -> None:
        if operation == "real_browser.open":
            prepare_open_target = getattr(self.backend, "prepare_open_target", None)
            if callable(prepare_open_target):
                prepare_open_target(params)
                return
            requested = str(params.get("target_origin") or self.backend.current_origin).strip()
            if requested and requested not in set(self.backend.allowed_origins):
                raise ActionKernelError("browser_origin_transition_not_authorized")
            self.backend.current_origin = requested or self.backend.current_origin
            return
        if operation == "real_browser.open_result":
            ref = str(params.get("ref") or params.get("result_ref") or "")
            if not ref.startswith(("link:", "result:", "evidence:")):
                raise ActionKernelError("browser_follow_ref_not_link")
            return
        if operation in {"real_browser.search", "real_browser.inspect_result", "real_browser.verify_extraction"}:
            return
        if operation == "real_browser.extract_evidence":
            return
        if operation == "real_browser.recover_session":
            return
        if operation == "real_browser.observe":
            return


def compile_canonical_browser_environment_state(
    *,
    backend: FakeBrowserReadOnlyBackend,
    operation: str,
    observation: dict[str, Any],
    available_actions: tuple[str, ...],
    mission_objective: str,
    remaining_provider_decisions: int,
    remaining_material_actions: int,
) -> dict[str, Any]:
    state = BrowserEnvironmentStateBuilder().build(
        snapshot=backend.snapshot(operation=operation),
        mission_objective=mission_objective,
        origin_hash=text_hash(backend.current_origin),
        selected_backend_id="fake_browser_readonly",
        actual_backend_id="fake_browser_readonly",
        session_backend_kind="fake_in_memory",
        extracted_text=" ".join(str(card.get("summary") or card.get("title") or "") for card in backend.evidence_cards[:12]),
        available_actions=available_actions,
        session_lease_status="ACTIVE",
        last_action={"operation": operation, "status": observation.get("status")},
        last_state_change={
            "before_state_hash": observation.get("page_state_hash"),
            "after_state_hash": observation.get("page_state_hash"),
            "evidence_delta": observation.get("evidence_delta"),
        },
        mission_progress={
            "verified_evidence_present": bool(backend.evidence_cards),
            "objective_satisfied": False,
            "finish_eligible": bool(backend.evidence_cards),
            "summary_present": False,
        },
    )
    safe_state = state.safe_model_dump()
    operational = safe_state.get("operational_snapshot") or {}
    fields = operational.get("fields") if isinstance(operational, dict) else {}
    return {
        "schema_version": "canonical_browser_environment_state_v1",
        "source_contract": safe_state.get("schema_version"),
        "task": {
            "objective_hash": text_hash(mission_objective),
            "progress": fields.get("mission_progress", {}).get("value", "unknown") if isinstance(fields, dict) else "unknown",
            "remaining_provider_decisions": remaining_provider_decisions,
            "remaining_material_actions": remaining_material_actions,
        },
        "browser": {
            "selected_backend_id": "fake_browser_readonly",
            "actual_backend_id": "fake_browser_readonly",
            "session_backend_kind": "fake_in_memory",
            "session_lease_status": "ACTIVE",
            "real_browser_runs": 0,
            "external_network_calls": 0,
        },
        "page": {
            "origin_hash": text_hash(backend.current_origin),
            "title": redact_operator_text(backend.page_title),
            "page_state_hash": observation.get("page_state_hash"),
            "page_type": (safe_state.get("page_state") or {}).get("page_kind_guess", "unknown"),
            "readiness": "observed",
        },
        "affordance_graph": {
            "available": [item for item in available_actions if str(item).startswith("real_browser_control.")],
            "order": list(BROWSER_COGNITIVE_AFFORDANCE_ORDER),
            "source": "ExecutableCapabilityGraph.routes",
        },
        "focus": {"selected_ref_hash": "", "selection_kind": "unknown"},
        "execution_signals": {
            "last_action": operation,
            "status": observation.get("status"),
            "failure_class": "",
            "evidence_delta": observation.get("evidence_delta"),
        },
        "memory": {
            "public_evidence": tuple(_safe_evidence_card(card) for card in backend.evidence_cards[:12]),
            "evidence_count": len(backend.evidence_cards),
        },
        "evaluation": {
            "typed_observation": redact_operator_value(observation.get("typed_observation") or {}),
            "unknowns": () if backend.evidence_cards else ("evidence_missing",),
            "contradictions": (),
        },
        "demand_load_handles": {
            "world_model_summary_hash": stable_hash(safe_state.get("world_model_summary") or {}),
            "operational_snapshot_hash": stable_hash(operational),
        },
        "limits": {
            "max_affordances": 12,
            "max_evidence_cards": 12,
            "max_depth": 2,
            "raw_dom_exposed": False,
            "cookies_exposed": False,
            "tokens_exposed": False,
            "selectors_as_protocol": False,
        },
        "data_not_authority": True,
        "authority_effect": "none",
        "can_grant_authority": False,
        "can_execute": False,
    }


def _typed_outcome(*, operation: str, evidence_cards: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    return {
        "operation": operation,
        "search_materiality": "MATERIAL_RESULTS" if operation == "real_browser.search" and evidence_cards else "NOT_APPLICABLE",
        "material_effect_observed": bool(evidence_cards),
        "evidence_delta": len(evidence_cards),
        "typed_status": "OBSERVED_PUBLIC_EVIDENCE" if evidence_cards else "OBSERVATION_ONLY",
    }


def _safe_evidence_card(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": redact_operator_text(str(card.get("evidence_id") or f"evidence:{stable_hash(card)[:24]}")),
        "kind": redact_operator_text(str(card.get("kind") or "unknown")),
        "title": redact_operator_text(str(card.get("title") or ""))[:220],
        "summary_hash": text_hash(str(card.get("summary") or "")),
        "confidence": _safe_confidence(card.get("confidence")),
    }


def _safe_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _physical_evidence_refs(
    *,
    operation: str,
    result_refs: tuple[str, ...],
    environment_state: dict[str, Any],
) -> tuple[str, ...]:
    if operation == "real_browser.observe":
        return tuple(dict.fromkeys(str(ref) for ref in result_refs if str(ref).strip()))
    refs = [str(ref) for ref in result_refs if str(ref).strip()]
    operational = environment_state.get("operational_snapshot") if isinstance(environment_state, dict) else {}
    fields = operational.get("fields") if isinstance(operational, dict) else {}
    inventory = fields.get("public_evidence_inventory") if isinstance(fields, dict) else {}
    value = inventory.get("value") if isinstance(inventory, dict) else {}
    for ref in value.get("evidence_refs", ()) if isinstance(value, dict) else ():
        text = str(ref).strip()
        if text:
            refs.append(text)
    return tuple(dict.fromkeys(refs))


def _physical_page_identity_hash(
    *,
    operation: str,
    result: ActionResult,
    environment_state: dict[str, Any],
    receipt_refs: tuple[str, ...],
) -> str:
    page_state = environment_state.get("page_state") if isinstance(environment_state, dict) else {}
    if isinstance(page_state, dict):
        page_hash = str(page_state.get("page_state_hash") or page_state.get("state_hash") or "").strip()
        if page_hash:
            return page_hash
    return stable_hash({"operation": operation, "result_hash": result.result_hash, "receipt_refs": receipt_refs})


def _internal_evidence_verification_status(*, operation: str, evidence_count: int) -> str:
    if operation == "real_browser.extract_evidence":
        return "passed" if evidence_count > 0 else "no_evidence_to_verify"
    if operation in {"real_browser.open", "real_browser.open_result", "real_browser.search"}:
        return "not_required_for_open_perception" if evidence_count > 0 else "no_evidence_to_verify"
    return "not_applicable"


__all__ = [
    "CanonicalBrowserReadOnlyAdapter",
    "FakeBrowserReadOnlyBackend",
    "PhysicalBrowserReadOnlyBackend",
    "MUTATING_BROWSER_OPERATIONS",
    "READ_ONLY_BROWSER_OPERATIONS",
    "compile_canonical_browser_environment_state",
]


def _engine_session_backend_kind(engine: RealBrowserEngine) -> str:
    return str(getattr(engine, "session_manager_backend_kind", "") or engine.__class__.__name__)


@dataclass(frozen=True)
class _SiteScope:
    canonical_site: str
    accepted_host_forms: tuple[str, ...]


def _public_read_only_site_scopes(allowed_origins: tuple[str, ...]) -> tuple[_SiteScope, ...]:
    scopes: list[_SiteScope] = []
    for origin in allowed_origins:
        host = _origin_host(origin)
        if not host:
            continue
        canonical = host[4:] if host.startswith("www.") else host
        accepted = tuple(dict.fromkeys((canonical, f"www.{canonical}")))
        scopes.append(_SiteScope(canonical_site=canonical, accepted_host_forms=accepted))
    if not scopes:
        scopes.append(_SiteScope(canonical_site="sqlite.org", accepted_host_forms=("sqlite.org", "www.sqlite.org")))
    unique: dict[str, _SiteScope] = {}
    for scope in scopes:
        unique.setdefault(scope.canonical_site, scope)
    return tuple(unique.values())


def _match_public_read_only_site_scope(*, target: dict[str, Any], site_scopes: tuple[_SiteScope, ...]) -> dict[str, Any]:
    normalized_host = str(target["normalized_host"])
    normalized_port = target.get("normalized_port")
    base = {
        "requested_url": target["requested_url"],
        "requested_url_hash": stable_hash(str(target["requested_url"])),
        "normalized_scheme": target["normalized_scheme"],
        "normalized_host": normalized_host,
        "normalized_port": normalized_port if normalized_port is not None else "default",
        "authority_match": "SiteScope",
        "risk_policy": "public_read_only_navigation_site_aliases_allowed",
        "matched": False,
        "matched_host_form": "",
        "canonical_site": "",
        "accepted_host_forms": (),
        "authority_expansion": False,
        "decision_rewritten": False,
    }
    for scope in site_scopes:
        if normalized_host not in set(scope.accepted_host_forms):
            continue
        match = {
            **base,
            "matched": normalized_port is None,
            "matched_host_form": normalized_host if normalized_port is None else "",
            "canonical_site": scope.canonical_site,
            "accepted_host_forms": scope.accepted_host_forms,
            "deny_reason": "" if normalized_port is None else "non_default_port_not_in_site_scope",
        }
        return match
    return {
        **base,
        "accepted_host_forms": tuple(dict.fromkeys(host for scope in site_scopes for host in scope.accepted_host_forms)),
        "deny_reason": "host_outside_site_scope",
    }


def _parse_browser_target(value: str) -> dict[str, Any]:
    requested = str(value or "").strip()
    if not requested:
        raise ActionKernelError("browser_open_target_missing")
    has_scheme = "://" in requested
    parsed = urlparse(requested if has_scheme else f"https://{requested}")
    scheme = (parsed.scheme or "https").lower()
    host = _normalize_hostname(parsed.hostname or "")
    if not host:
        raise ActionKernelError("browser_open_target_host_missing")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ActionKernelError("browser_open_target_port_invalid") from exc
    normalized_port = _normalized_url_port(scheme=scheme, port=port)
    return {
        "requested_url": requested,
        "target_url": requested if has_scheme else _browser_target_url_with_default_scheme(parsed=parsed, host=host),
        "normalized_scheme": scheme,
        "normalized_host": host,
        "normalized_port": normalized_port,
    }


def _origin_host(value: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    return _normalize_hostname(parsed.hostname or text.split("/", 1)[0])


def _normal_browser_target_url(value: str) -> str:
    return str(_parse_browser_target(value)["target_url"])


def _normalize_hostname(host: str) -> str:
    text = str(host or "").strip().rstrip(".").lower()
    if not text:
        return ""
    try:
        return text.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return text


def _normalized_url_port(*, scheme: str, port: int | None) -> int | None:
    if port is None:
        return None
    if scheme == "http" and port == 80:
        return None
    if scheme == "https" and port == 443:
        return None
    return int(port)


def _browser_target_url_with_default_scheme(*, parsed: Any, host: str) -> str:
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    return urlunparse(("https", host, path, "", parsed.query, parsed.fragment))


def _set_engine_target_url(engine: RealBrowserEngine, target_url: str) -> None:
    setter = getattr(engine, "set_target_url", None)
    if callable(setter):
        setter(target_url)
        return
    if hasattr(engine, "target_url"):
        setattr(engine, "target_url", target_url)
