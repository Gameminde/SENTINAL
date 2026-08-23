from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sentinel import cli
from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.canonical_browser_readonly_adapter import PhysicalBrowserReadOnlyBackend
from sentinel.operator.canonical_core import (
    RootMissionCancellationToken,
    build_workspace_browser_readonly_capability_graph,
    run_canonical_product_mission,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import OperatorMissionStatus
from sentinel.operator.provider_mesh import ProviderMesh, ProviderMeshProviderSpec
from sentinel.operator.real_browser_control_runtime import (
    BOUNDED_URL_AUTHORITY_REF,
    RealBrowserControlRuntimeError,
    RealBrowserEngineElement,
    RealBrowserEngineSnapshot,
    SENTINEL_CHROMIUM_BACKEND_ID,
    build_canonical_real_browser_engine_from_env,
)
from sentinel.organs.browser.cloak_backend import _playwright_open_failure_code


class ScriptedModelClient:
    def __init__(self, decisions: list[dict[str, Any]]) -> None:
        self._decisions = list(decisions)
        self.requests: list[Any] = []

    def complete(self, request: Any) -> dict[str, Any]:
        self.requests.append(request)
        if not self._decisions:
            raise AssertionError("scripted model decision exhausted")
        return self._decisions.pop(0)


class ScriptedThenRateLimitModelClient(ScriptedModelClient):
    def complete(self, request: Any) -> dict[str, Any]:
        if self._decisions:
            return super().complete(request)
        self.requests.append(request)
        raise RuntimeError("provider_failure_PROVIDER_RATE_LIMIT_http_429")


class ScriptedThenProviderAuthErrorModelClient(ScriptedModelClient):
    def complete(self, request: Any) -> dict[str, Any]:
        if self._decisions:
            return super().complete(request)
        self.requests.append(request)
        raise RuntimeError("provider_failure_PROVIDER_AUTH_ERROR_credential_rejected_http_401")


class ScriptedThenTransportJsonErrorModelClient(ScriptedModelClient):
    def complete(self, request: Any) -> dict[str, Any]:
        if self._decisions:
            return super().complete(request)
        self.requests.append(request)
        raise RuntimeError("provider_failure_PROVIDER_TRANSPORT_ERROR_local_JSONDecodeError")


class InstrumentedSentinelChromiumReadOnlyEngine:
    browser_backend_id = SENTINEL_CHROMIUM_BACKEND_ID
    session_manager_backend_kind = "sentinel_chromium"

    def __init__(self) -> None:
        self.open_count = 0
        self.observe_count = 0
        self.click_count = 0
        self.type_count = 0
        self.assert_count = 0
        self.select_count = 0
        self.extract_count = 0
        self.press_count = 0
        self.wait_count = 0
        self.scroll_count = 0
        self.close_count = 0
        self.bound_authority: Any | None = None
        self.bound_root_session_id = ""
        self.target_urls: list[str] = []
        self.closed = False

    @property
    def safe_url_origin_hash(self) -> str:
        return stable_hash({"scheme": "https", "host": "sqlite.org", "port": None})

    def bind_authority(self, authority: Any) -> None:
        self.bound_authority = authority

    def bind_root_session_id(self, root_session_id: str) -> None:
        self.bound_root_session_id = root_session_id

    def set_target_url(self, url: str) -> None:
        if self.target_urls and self.target_urls[-1] == url:
            return
        self.target_urls.append(url)

    def open(self) -> RealBrowserEngineSnapshot:
        self.open_count += 1
        self.closed = False
        return self._snapshot("open")

    def observe(self) -> RealBrowserEngineSnapshot:
        self.observe_count += 1
        return self._snapshot("observe")

    def extract_text(self) -> tuple[str, RealBrowserEngineSnapshot]:
        self.extract_count += 1
        return (
            "SQLite generated columns are columns whose values are computed from expressions.",
            self._snapshot("extract"),
        )

    def close(self) -> None:
        self.close_count += 1
        self.closed = True

    def _snapshot(self, stage: str) -> RealBrowserEngineSnapshot:
        return RealBrowserEngineSnapshot(
            page_title="SQLite Generated Columns",
            state_hash=stable_hash({"stage": stage, "open_count": self.open_count, "extract_count": self.extract_count}),
            elements=(
                RealBrowserEngineElement(
                    ref="link:generated-columns",
                    role="link",
                    name="Generated Columns",
                    text_preview="Generated Columns",
                ),
            ),
        )


class CancellingSentinelChromiumReadOnlyEngine(InstrumentedSentinelChromiumReadOnlyEngine):
    def __init__(self, token: RootMissionCancellationToken) -> None:
        super().__init__()
        self._token = token

    def observe(self) -> RealBrowserEngineSnapshot:
        snapshot = super().observe()
        self._token.cancel("operator_cancelled_during_physical_browser_effect")
        return snapshot


class FailingOpenSentinelChromiumReadOnlyEngine(InstrumentedSentinelChromiumReadOnlyEngine):
    def open(self) -> RealBrowserEngineSnapshot:
        self.open_count += 1
        raise RealBrowserControlRuntimeError("sentinel_chromium_browser_executable_missing")


def test_canonical_browser_engine_factory_does_not_require_cloak_configuration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("SENTINEL_BROWSER_TEST_URL", raising=False)
    monkeypatch.delenv("CLOAKBROWSER_BINARY_PATH", raising=False)
    monkeypatch.delenv("SENTINEL_REQUIRE_CLOAKBROWSER_BINARY_PATH", raising=False)

    engine = build_canonical_real_browser_engine_from_env(capture_root=tmp_path / "capture")

    assert engine.browser_backend_id == SENTINEL_CHROMIUM_BACKEND_ID
    assert engine.session_manager_backend_kind == "sentinel_chromium"
    assert getattr(engine, "target_url", None) == "about:blank"


def test_sentinel_chromium_classifies_missing_playwright_chromium_without_raw_path() -> None:
    class PlaywrightLaunchError(Exception):
        pass

    exc = PlaywrightLaunchError(
        "Executable doesn't exist at C:/private/browser/path/chromium.exe\n"
        "Please run the following command to download new browsers:\n"
        "python -m playwright install chromium"
    )

    assert _playwright_open_failure_code(exc) == "sentinel_chromium_browser_executable_missing"


def test_physical_browser_open_failure_produces_terminal_receipt_and_failure_packet(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = FailingOpenSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(
        engine=engine,
        kernel=kernel,
        allowed_origins=("sqlite.org",),
    )
    model = ScriptedModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"url": "https://sqlite.org/datatype3.html"},
            },
            {
                "capability": "sentinel_loop",
                "operation": "finish",
                "arguments": {"answer": "SQLite documentation was checked."},
            },
        ]
    )

    result = run_canonical_product_mission(
        objective="Open official SQLite documentation with the governed browser.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c5_physical_browser_open_failure_receipt",
        max_provider_decisions=2,
        max_material_actions=2,
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "blocked"
    assert result.final_reason == "PROVIDER_DECISION_BUDGET_EXHAUSTED"
    assert engine.open_count == 1
    assert result.receipts
    receipt = result.receipts[0]
    assert receipt.capability == "real_browser_control"
    assert receipt.operation == "real_browser.open"
    assert receipt.status == "recoverable_failed"
    assert receipt.material_action is False
    observation = receipt.safe_observation
    assert observation["status"] == "recoverable_failed"
    assert observation["failure_code"] == "sentinel_chromium_browser_executable_missing"
    assert observation["product_action_kernel_dispatch"] is True
    assert observation["browser_terminal_receipt"]["status"] == "recoverable_failed"
    assert observation["runtime_failure_fact"]["attempted_operation"] == "real_browser.open"
    assert observation["model_visible_body_failure_packet"]["attempted_operation"] == "real_browser.open"
    events = kernel.store.load_events(result.root_mission_id)
    assert any(event.event_type == "canonical_model_final_answer_missing_evidence" for event in events)


def test_physical_browser_recover_session_is_routed_to_terminal_receipt(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(
        engine=engine,
        kernel=kernel,
        allowed_origins=("sqlite.org",),
    )
    model = ScriptedModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"url": "https://sqlite.org/gencol.html"},
            },
            {
                "capability": "real_browser_control",
                "operation": "real_browser.recover_session",
                "arguments": {"failure_ref": "receipt:previous"},
            },
            {
                "capability": "sentinel_loop",
                "operation": "finish",
                "arguments": {"answer": "The governed browser session was recovered."},
            },
        ]
    )

    result = run_canonical_product_mission(
        objective="Recover the current governed browser session.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c5_physical_browser_recover_session_receipt",
        max_provider_decisions=4,
        max_material_actions=4,
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "completed"
    assert result.final_reason == "model_selected_finish"
    assert engine.open_count == 1
    assert engine.observe_count >= 1
    assert [receipt.operation for receipt in result.receipts] == [
        "real_browser.open",
        "real_browser.recover_session",
    ]
    assert result.receipts[1].status == "completed"


def test_public_product_physical_browser_readiness_after_mission_record_and_before_provider(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    observed: dict[str, Any] = {"factory_called": False, "model_called": False}

    def _factory() -> InstrumentedSentinelChromiumReadOnlyEngine:
        observed["factory_called"] = True
        missions = kernel.list_missions()
        observed["mission_count_at_factory"] = len(missions)
        observed["mission_record_verified_at_factory"] = bool(
            missions and kernel.store.verify_record(missions[0].mission_id)
        )
        return InstrumentedSentinelChromiumReadOnlyEngine()

    class FailingIfCalledModel:
        def complete(self, request: Any) -> dict[str, Any]:
            observed["model_called"] = True
            raise AssertionError("provider_allocated_before_browser_readiness")

    backend = PhysicalBrowserReadOnlyBackend(kernel=kernel, engine_factory=_factory)

    result = run_canonical_product_mission(
        objective="Open official SQLite generated columns documentation.",
        workspace_root=workspace,
        model_client=FailingIfCalledModel(),
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c5_browser_readiness_before_provider",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert observed["factory_called"] is True
    assert observed["mission_record_verified_at_factory"] is True
    assert observed["model_called"] is True
    assert result.mission_record_created_before_provider is True


def test_public_product_browser_readiness_failure_terminalizes_with_receipt_before_provider(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")

    def _factory() -> InstrumentedSentinelChromiumReadOnlyEngine:
        raise RealBrowserControlRuntimeError("sentinel_chromium_backend_construction_failed_for_test")

    class FailingIfCalledModel:
        def complete(self, request: Any) -> dict[str, Any]:
            raise AssertionError("provider_called_after_browser_readiness_failure")

    backend = PhysicalBrowserReadOnlyBackend(kernel=kernel, engine_factory=_factory)

    result = run_canonical_product_mission(
        objective="Open official SQLite generated columns documentation.",
        workspace_root=workspace,
        model_client=FailingIfCalledModel(),
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c5_browser_readiness_failure_terminalizes",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    record = kernel.store.load_record(result.root_mission_id)

    assert result.status == "blocked"
    assert result.final_reason == "BROWSER_BACKEND_READINESS_FAILED"
    assert result.provider_decision_count == 0
    assert result.mission_record_created_before_provider is True
    assert record.status is OperatorMissionStatus.BLOCKED
    assert result.receipts
    assert result.receipts[0].operation == "browser_backend_readiness"
    assert result.receipts[0].status == "blocked"
    assert result.cleanup_completed is True


def test_public_canonical_product_run_can_enable_sovereign_physical_browser(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    workspace = _workspace(tmp_path)
    script = tmp_path / "decisions.jsonl"
    script.write_text(
        "\n".join(
            [
                json.dumps({"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}}),
                json.dumps({"capability": "sentinel_loop", "operation": "finish", "arguments": {"answer": "Observed."}}),
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("SENTINEL_BROWSER_TEST_URL", raising=False)
    monkeypatch.delenv("CLOAKBROWSER_BINARY_PATH", raising=False)
    monkeypatch.delenv("SENTINEL_REQUIRE_CLOAKBROWSER_BINARY_PATH", raising=False)
    monkeypatch.setattr(
        cli,
        "build_canonical_real_browser_engine_from_env",
        lambda *, capture_root=None: InstrumentedSentinelChromiumReadOnlyEngine(),
    )

    exit_code = cli.main(
        [
            "canonical-product-run",
            "--objective",
            "Observe the governed browser page.",
            "--workspace",
            str(workspace),
            "--run-root",
            str(tmp_path / "runs"),
            "--decision-script",
            str(script),
            "--provider-model",
            "scripted-local/model",
            "--enable-browser-readonly-physical",
            "--browser-allowed-origin",
            "sqlite.org",
            "--json",
        ]
    )

    output = capsys.readouterr()
    payload = json.loads(output.out.strip())

    assert exit_code == 0
    assert payload["status"] == "completed"
    assert payload["public_product_spine"]["browser_readonly_physical_enabled"] is True
    assert payload["public_product_spine"]["browser_readonly_fake_enabled"] is False
    assert payload["public_product_spine"]["browser_backend_id"] == SENTINEL_CHROMIUM_BACKEND_ID
    assert payload["public_product_spine"]["cloak_dependency"] is False
    assert payload["product_receipt_refs"]


def test_physical_browser_readonly_backend_runs_through_single_spine_with_sovereign_receipts(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(engine=engine, kernel=kernel)
    model = ScriptedModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"url": "https://sqlite.org/gencol.html"},
            },
            {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}},
            {"capability": "real_browser_control", "operation": "real_browser.extract_evidence", "arguments": {}},
            {
                "capability": "sentinel_loop",
                "operation": "finish",
                "arguments": {"answer": "SQLite generated columns are computed from expressions."},
            },
        ]
    )

    result = run_canonical_product_mission(
        objective="Find official SQLite documentation about generated columns.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c5_physical_browser_single_spine",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    record = kernel.store.load_record(result.root_mission_id)
    events = kernel.store.load_events(result.root_mission_id)
    third_turn_state = model.requests[2].canonical_state.safe_model_dump()
    real_browser_receipts = sorted(
        (kernel.store.mission_dir(result.root_mission_id) / "real_browser_control" / "receipts").glob("*.json")
    )
    first_browser_receipt = json.loads(real_browser_receipts[0].read_text(encoding="utf-8"))

    assert result.status == "completed"
    assert result.provider_decision_count == 4
    assert result.material_action_count == 3
    assert record.status is OperatorMissionStatus.COMPLETED
    assert result.proof_root.root_mission_id == record.mission_id
    assert result.proof_root.receipt_refs == tuple(record.receipt_refs)
    assert result.proof_root.receipt_artifacts_verified is True
    assert engine.bound_authority is not None
    assert BOUNDED_URL_AUTHORITY_REF in engine.bound_authority.allowed_domains
    assert "real_browser.open" in engine.bound_authority.allowed_actions
    assert engine.open_count == 1
    assert engine.observe_count >= 1
    assert engine.extract_count == 1
    assert engine.close_count == 1
    assert backend.provider_calls == 0
    assert backend.real_browser_runs == 3
    assert backend.external_network_calls == 0
    assert backend.cleanup_count == 1
    assert backend.lease_released is True
    assert real_browser_receipts
    assert first_browser_receipt["selected_backend_id"] == SENTINEL_CHROMIUM_BACKEND_ID
    assert first_browser_receipt["actual_backend_id"] == SENTINEL_CHROMIUM_BACKEND_ID
    assert first_browser_receipt["session_backend_kind"] == "sentinel_chromium"
    assert first_browser_receipt.get("backend_mismatch") is False
    assert all(receipt.capability == "real_browser_control" for receipt in result.receipts)
    assert result.receipts[0].safe_observation["backend_kind"] == "physical"
    assert result.receipts[0].safe_observation["selected_backend_id"] == SENTINEL_CHROMIUM_BACKEND_ID
    assert result.receipts[0].safe_observation["actual_backend_id"] == SENTINEL_CHROMIUM_BACKEND_ID
    assert third_turn_state["browser_environment_state"]["browser"]["selected_backend_id"] == SENTINEL_CHROMIUM_BACKEND_ID
    assert third_turn_state["browser_environment_state"]["browser"]["actual_backend_id"] == SENTINEL_CHROMIUM_BACKEND_ID
    assert any(event.event_type == "canonical_browser_readonly_cleanup_completed" for event in events)


def test_physical_browser_open_uses_model_url_only_at_authorized_dispatch(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(
        engine=engine,
        kernel=kernel,
        allowed_origins=("sqlite.org",),
    )
    model = ScriptedModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"url": "https://sqlite.org/gencol.html"},
            },
            {
                "capability": "sentinel_loop",
                "operation": "finish",
                "arguments": {"answer": "Opened governed SQLite documentation."},
            },
        ]
    )

    result = run_canonical_product_mission(
        objective="Open a governed browser page.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c5_physical_browser_authorized_url_dispatch",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "completed"
    assert engine.open_count == 1
    assert engine.target_urls == ["https://sqlite.org/gencol.html"]


def test_physical_browser_site_scope_allows_public_readonly_apex_www_and_normalized_forms(tmp_path: Path) -> None:
    cases = (
        ("sqlite.org", "sqlite.org"),
        ("www.sqlite.org", "www.sqlite.org"),
        ("https://sqlite.org/gencol.html", "sqlite.org"),
        ("https://www.sqlite.org/gencol.html", "www.sqlite.org"),
        ("https://WWW.SQLITE.ORG/gencol.html", "www.sqlite.org"),
        ("https://sqlite.org./gencol.html", "sqlite.org"),
        ("http://sqlite.org:80/gencol.html", "sqlite.org"),
        ("https://sqlite.org:443/gencol.html", "sqlite.org"),
    )
    for index, (url, expected_host) in enumerate(cases):
        result, engine = _run_physical_open(tmp_path / f"allowed_{index}", url=url, allowed_origins=("sqlite.org",))

        assert result.status == "completed"
        assert engine.open_count == 1
        match = result.receipts[0].safe_observation["site_authority_match"]
        assert match["requested_url"] == url
        assert match["normalized_host"] == expected_host
        assert match["authority_match"] == "SiteScope"
        assert match["canonical_site"] == "sqlite.org"
        assert match["matched"] is True
        assert match["risk_policy"] == "public_read_only_navigation_site_aliases_allowed"


def test_physical_browser_site_scope_denies_suffix_subdomain_and_cross_site_redirect_targets(tmp_path: Path) -> None:
    cases = (
        "https://sqlite.org.attacker.com/gencol.html",
        "https://docs.sqlite.org/gencol.html",
        "https://evil.sqlite.org/gencol.html",
        "https://example.com/redirect?target=https://sqlite.org/gencol.html",
        "https://sqlite.org:444/gencol.html",
    )
    for index, url in enumerate(cases):
        result, engine = _run_physical_open(tmp_path / f"denied_{index}", url=url, allowed_origins=("sqlite.org",))

        assert result.status == "blocked"
        assert result.blocked_reason_detail == "browser_origin_transition_not_authorized"
        assert engine.open_count == 0
        assert engine.target_urls == []


def test_provider_mesh_checkpoints_rate_limit_and_resumes_without_replaying_browser_receipt(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(
        engine=engine,
        kernel=kernel,
        allowed_origins=("sqlite.org",),
    )
    primary = ScriptedThenRateLimitModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"url": "https://www.sqlite.org/gencol.html"},
            },
            {
                "capability": "real_browser_control",
                "operation": "real_browser.extract_evidence",
                "arguments": {},
            },
        ]
    )
    fallback = ScriptedModelClient(
        [
            {
                "capability": "sentinel_loop",
                "operation": "finish",
                "arguments": {"answer": "SQLite generated columns are documented by the official SQLite site."},
            }
        ]
    )
    mesh = ProviderMesh(
        providers=(
            ProviderMeshProviderSpec(
                provider_id="openrouter",
                backend_id="openrouter_chat_completions",
                model_id="z-ai/glm-5.2",
                client=primary,
                role="primary",
            ),
            ProviderMeshProviderSpec(
                provider_id="openrouter",
                backend_id="openrouter_chat_completions",
                model_id="moonshotai/kimi-k2.7-code",
                client=fallback,
                role="fallback_1",
            ),
        ),
        fallback_order=("z-ai/glm-5.2", "moonshotai/kimi-k2.7-code"),
    )

    result = run_canonical_product_mission(
        objective="Find official SQLite documentation explaining generated columns and provide a short useful answer.",
        workspace_root=workspace,
        model_client=mesh,
        provider_model="openrouter/z-ai/glm-5.2",
        kernel=kernel,
        session_id="c6_provider_mesh_resume",
        max_provider_decisions=6,
        max_material_actions=4,
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "completed"
    assert result.final_reason == "model_selected_finish"
    assert result.provider_decision_count == 4
    assert result.material_action_count == 2
    assert engine.open_count == 1
    assert engine.extract_count == 1
    assert len(result.receipts) == 2
    assert result.receipts[0].operation == "real_browser.open"
    assert result.receipts[1].operation == "real_browser.extract_evidence"
    assert fallback.requests
    resumed_state = fallback.requests[0].canonical_state.safe_model_dump()
    assert resumed_state["material_action_count"] == 2
    assert resumed_state["evidence_refs"]
    assert mesh.safe_transitions[0]["fallback_reason"] == "provider_failure_PROVIDER_RATE_LIMIT_http_429"
    assert mesh.safe_transitions[0]["requested_model"] == "z-ai/glm-5.2"
    assert mesh.safe_transitions[0]["actual_model"] == "z-ai/glm-5.2"
    assert mesh.safe_transitions[0]["next_model"] == "moonshotai/kimi-k2.7-code"
    assert mesh.safe_transitions[0]["mission_state_hash"] == resumed_state["state_hash"]
    assert mesh.safe_transitions[0]["previous_receipt_root"]
    events = kernel.store.load_events(result.root_mission_id)
    assert any(event.event_type == "canonical_provider_mesh_turn_failed" for event in events)


def test_provider_mesh_checkpoints_auth_error_and_resumes_explicit_fallback_without_replaying_browser_receipt(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(
        engine=engine,
        kernel=kernel,
        allowed_origins=("sqlite.org",),
    )
    primary = ScriptedThenProviderAuthErrorModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"url": "https://www.sqlite.org/gencol.html"},
            },
            {
                "capability": "real_browser_control",
                "operation": "real_browser.extract_evidence",
                "arguments": {},
            },
        ]
    )
    fallback = ScriptedModelClient(
        [
            {
                "capability": "sentinel_loop",
                "operation": "finish",
                "arguments": {"answer": "SQLite generated columns evidence was already collected before fallback."},
            }
        ]
    )
    mesh = ProviderMesh(
        providers=(
            ProviderMeshProviderSpec(
                provider_id="tokenrouter",
                backend_id="tokenrouter_chat_completions",
                model_id="qwen/qwen3.8-max-free",
                client=primary,
                role="primary",
            ),
            ProviderMeshProviderSpec(
                provider_id="opencode",
                backend_id="opencode_responses",
                model_id="muse-spark-1.2-contributor-free",
                client=fallback,
                role="fallback_1",
            ),
        ),
        fallback_order=("qwen/qwen3.8-max-free", "muse-spark-1.2-contributor-free"),
    )

    result = run_canonical_product_mission(
        objective="Find official SQLite documentation explaining generated columns and provide a short useful answer.",
        workspace_root=workspace,
        model_client=mesh,
        provider_model="tokenrouter/qwen/qwen3.8-max-free",
        kernel=kernel,
        session_id="c6_provider_mesh_auth_error_resume",
        max_provider_decisions=6,
        max_material_actions=4,
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "completed"
    assert result.final_reason == "model_selected_finish"
    assert result.provider_decision_count == 4
    assert result.material_action_count == 2
    assert engine.open_count == 1
    assert engine.extract_count == 1
    assert len(result.receipts) == 2
    assert result.receipts[0].operation == "real_browser.open"
    assert result.receipts[1].operation == "real_browser.extract_evidence"
    assert fallback.requests
    resumed_state = fallback.requests[0].canonical_state.safe_model_dump()
    assert resumed_state["material_action_count"] == 2
    assert resumed_state["evidence_refs"]
    assert any(
        observation.get("provider_handoff") == "fallback"
        and observation.get("previous_model") == "qwen/qwen3.8-max-free"
        and observation.get("next_model") == "muse-spark-1.2-contributor-free"
        and observation.get("browser_actions_replayed") is False
        for observation in resumed_state["recent_observations"]
    )
    assert mesh.safe_transitions[0]["fallback_reason"] == "provider_failure_PROVIDER_AUTH_ERROR_credential_rejected_http_401"
    assert mesh.safe_transitions[0]["provider_turn_terminalized"] is True
    assert mesh.safe_transitions[0]["browser_actions_replayed"] is False
    assert mesh.safe_transitions[0]["fallback_silent"] is False
    assert mesh.safe_transitions[0]["mission_state_hash"] == resumed_state["state_hash"]
    events = kernel.store.load_events(result.root_mission_id)
    turn_failure_events = [event for event in events if event.event_type == "canonical_provider_mesh_turn_failed"]
    assert turn_failure_events
    assert turn_failure_events[0].metadata["loop_event_type"] == "model/request-error"


def test_provider_mesh_checkpoints_transport_json_error_and_resumes_explicit_fallback_without_replaying_browser_receipt(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(
        engine=engine,
        kernel=kernel,
        allowed_origins=("sqlite.org",),
    )
    primary = ScriptedThenTransportJsonErrorModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"url": "https://www.sqlite.org/wal.html"},
            },
            {
                "capability": "real_browser_control",
                "operation": "real_browser.extract_evidence",
                "arguments": {},
            },
        ]
    )
    fallback = ScriptedModelClient(
        [
            {
                "capability": "sentinel_loop",
                "operation": "finish",
                "arguments": {"answer": "SQLite WAL evidence was already collected before fallback."},
            }
        ]
    )
    mesh = ProviderMesh(
        providers=(
            ProviderMeshProviderSpec(
                provider_id="opencode_chat",
                backend_id="opencode_chat_completions",
                model_id="x-preview-f-free",
                client=primary,
                role="primary",
            ),
            ProviderMeshProviderSpec(
                provider_id="opencode",
                backend_id="opencode_responses",
                model_id="muse-spark-1.2-contributor-free",
                client=fallback,
                role="fallback_1",
            ),
        ),
        fallback_order=("x-preview-f-free", "muse-spark-1.2-contributor-free"),
    )

    result = run_canonical_product_mission(
        objective="Use official SQLite documentation to explain WAL and produce a short useful answer.",
        workspace_root=workspace,
        model_client=mesh,
        provider_model="opencode_chat/x-preview-f-free",
        kernel=kernel,
        session_id="c6_provider_mesh_transport_json_error_resume",
        max_provider_decisions=6,
        max_material_actions=4,
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "completed"
    assert result.final_reason == "model_selected_finish"
    assert result.provider_decision_count == 4
    assert result.material_action_count == 2
    assert engine.open_count == 1
    assert engine.extract_count == 1
    assert fallback.requests
    resumed_state = fallback.requests[0].canonical_state.safe_model_dump()
    assert resumed_state["material_action_count"] == 2
    assert resumed_state["evidence_refs"]
    assert mesh.safe_transitions[0]["fallback_reason"] == "provider_failure_PROVIDER_TRANSPORT_ERROR_local_JSONDecodeError"
    assert mesh.safe_transitions[0]["fallback_silent"] is False
    assert mesh.safe_transitions[0]["browser_actions_replayed"] is False


def test_provider_mesh_no_fallback_surfaces_typed_terminal_blocker(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(
        engine=engine,
        kernel=kernel,
        allowed_origins=("sqlite.org",),
    )
    primary = ScriptedThenRateLimitModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"url": "https://www.sqlite.org/wal.html"},
            },
        ]
    )
    fallback = ScriptedThenProviderAuthErrorModelClient([])
    mesh = ProviderMesh(
        providers=(
            ProviderMeshProviderSpec(
                provider_id="nvidia",
                backend_id="nvidia_openai_compatible_chat",
                model_id="minimaxai/minimax-m3",
                client=primary,
                role="primary",
            ),
            ProviderMeshProviderSpec(
                provider_id="opencode_chat",
                backend_id="opencode_chat_completions",
                model_id="x-preview-f-free",
                client=fallback,
                role="fallback_1",
            ),
        ),
        fallback_order=("minimaxai/minimax-m3", "x-preview-f-free"),
    )

    result = run_canonical_product_mission(
        objective="Open official SQLite documentation.",
        workspace_root=workspace,
        model_client=mesh,
        provider_model="nvidia/minimaxai/minimax-m3",
        kernel=kernel,
        session_id="c6_provider_mesh_no_fallback_typed_blocker",
        max_provider_decisions=4,
        max_material_actions=4,
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "blocked"
    assert (
        result.blocked_reason_detail
        == "provider_mesh_no_fallback_available:provider_failure_PROVIDER_AUTH_ERROR_credential_rejected_http_401"
    )
    assert engine.open_count == 1
    assert len(result.receipts) == 1


def test_provider_mesh_planned_handoff_resumes_same_mission_without_replaying_browser_receipt(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(
        engine=engine,
        kernel=kernel,
        allowed_origins=("sqlite.org",),
    )
    phase_a = ScriptedModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"url": "https://www.sqlite.org/wal.html"},
            },
            {
                "capability": "real_browser_control",
                "operation": "real_browser.extract_evidence",
                "arguments": {},
            },
        ]
    )
    phase_b = ScriptedModelClient(
        [
            {
                "capability": "sentinel_loop",
                "operation": "finish",
                "arguments": {"answer": "SQLite WAL evidence was collected before the planned handoff."},
            }
        ]
    )
    mesh = ProviderMesh(
        providers=(
            ProviderMeshProviderSpec(
                provider_id="opencode_chat",
                backend_id="opencode_chat_completions",
                model_id="x-preview-f-free",
                client=phase_a,
                role="phase_a",
            ),
            ProviderMeshProviderSpec(
                provider_id="opencode",
                backend_id="opencode_responses",
                model_id="muse-spark-1.2-contributor-free",
                client=phase_b,
                role="phase_b",
            ),
        ),
        fallback_order=("x-preview-f-free", "muse-spark-1.2-contributor-free"),
        planned_handoff_after_material_actions=2,
        planned_handoff_reason="sqlite_evidence_phase_a_complete",
    )

    result = run_canonical_product_mission(
        objective="Use official SQLite documentation to explain WAL and produce a short useful answer.",
        workspace_root=workspace,
        model_client=mesh,
        provider_model="opencode_chat/x-preview-f-free",
        kernel=kernel,
        session_id="c6l_planned_handoff",
        max_provider_decisions=6,
        max_material_actions=4,
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "completed"
    assert result.final_reason == "model_selected_finish"
    assert result.provider_decision_count == 3
    assert result.material_action_count == 2
    assert engine.open_count == 1
    assert engine.extract_count == 1
    assert phase_b.requests
    resumed_state = phase_b.requests[0].canonical_state.safe_model_dump()
    assert resumed_state["root_mission_id"] == result.root_mission_id
    assert resumed_state["material_action_count"] == 2
    assert resumed_state["evidence_refs"]
    assert any(
        observation.get("provider_handoff") == "planned"
        and observation.get("previous_model") == "x-preview-f-free"
        and observation.get("next_model") == "muse-spark-1.2-contributor-free"
        for observation in resumed_state["recent_observations"]
    )
    assert mesh.safe_transitions[0]["handoff_reason"] == "sqlite_evidence_phase_a_complete"
    assert mesh.safe_transitions[0]["previous_receipt_root"]
    assert mesh.safe_transitions[0]["browser_actions_replayed"] is False
    events = kernel.store.load_events(result.root_mission_id)
    assert any(event.event_type == "canonical_provider_mesh_planned_handoff" for event in events)


def test_physical_browser_open_blocks_cross_origin_before_engine_call(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(
        engine=engine,
        kernel=kernel,
        allowed_origins=("sqlite.org",),
    )
    model = ScriptedModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"url": "https://example.com/escape"},
            },
        ]
    )

    result = run_canonical_product_mission(
        objective="Do not allow a browser origin escape.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c5_physical_browser_cross_origin_denied",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "blocked"
    assert result.blocked_reason_detail == "browser_origin_transition_not_authorized"
    assert engine.open_count == 0
    assert engine.target_urls == []


def test_physical_browser_authority_carries_concrete_backend_origins_to_session_manager(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(
        engine=engine,
        kernel=kernel,
        allowed_origins=("sqlite.org", "www.sqlite.org"),
    )
    model = ScriptedModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"target_origin": "sqlite.org"},
            },
            {
                "capability": "sentinel_loop",
                "operation": "finish",
                "arguments": {"answer": "Browser authority includes concrete backend origins."},
            },
        ]
    )

    result = run_canonical_product_mission(
        objective="Open a bounded public browser target.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c5_physical_browser_concrete_origin_authority",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )

    assert result.status == "completed"
    assert engine.bound_authority is not None
    assert BOUNDED_URL_AUTHORITY_REF in engine.bound_authority.allowed_domains
    assert "sqlite.org" in engine.bound_authority.allowed_domains
    assert "www.sqlite.org" in engine.bound_authority.allowed_domains


def test_physical_browser_authority_denial_blocks_before_engine_call(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(engine=engine, kernel=kernel)
    model = ScriptedModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"url": "https://sqlite.org/gencol.html"},
            },
        ]
    )

    result = run_canonical_product_mission(
        objective="Browser read authority must be required before any physical browser effect.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c5_physical_browser_authority_denial",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "none"),
    )

    assert result.status == "blocked"
    assert result.final_reason == "EFFECT_DISPATCH_FAILED"
    assert result.blocked_reason_detail == "canonical_authority_required:browser_read"
    assert engine.open_count == 0
    assert engine.observe_count == 0
    assert backend.real_browser_runs == 0
    assert backend.cleanup_count == 1
    assert backend.lease_released is True
    assert result.cleanup_completed is True


def test_physical_browser_cancellation_after_dispatch_preserves_terminal_receipt_and_cleans_up(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    token = RootMissionCancellationToken()
    engine = CancellingSentinelChromiumReadOnlyEngine(token)
    backend = PhysicalBrowserReadOnlyBackend(engine=engine, kernel=kernel)
    model = ScriptedModelClient(
        [
            {"capability": "real_browser_control", "operation": "real_browser.observe", "arguments": {}},
        ]
    )

    result = run_canonical_product_mission(
        objective="Cancellation during a physical browser effect must clean up without fabricating completion.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id="c5_physical_browser_cancellation",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
        cancellation_token=token,
    )

    real_browser_receipts = sorted(
        (kernel.store.mission_dir(result.root_mission_id) / "real_browser_control" / "receipts").glob("*.json")
    )

    assert result.status == "blocked"
    assert result.final_reason == "EFFECT_DISPATCH_FAILED"
    assert result.blocked_reason_detail == "root_mission_cancelled_during_browser_effect"
    assert engine.observe_count == 1
    assert engine.close_count == 1
    assert backend.cleanup_count == 1
    assert backend.lease_released is True
    assert result.cleanup_completed is True
    assert real_browser_receipts
    assert result.receipts == ()


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "notes.md").write_text("local fixture only\n", encoding="utf-8")
    return workspace


def _run_physical_open(
    tmp_path: Path,
    *,
    url: str,
    allowed_origins: tuple[str, ...],
) -> tuple[Any, InstrumentedSentinelChromiumReadOnlyEngine]:
    workspace = _workspace(tmp_path)
    kernel = MissionKernel(run_root=tmp_path / "runs")
    engine = InstrumentedSentinelChromiumReadOnlyEngine()
    backend = PhysicalBrowserReadOnlyBackend(
        engine=engine,
        kernel=kernel,
        allowed_origins=allowed_origins,
    )
    model = ScriptedModelClient(
        [
            {
                "capability": "real_browser_control",
                "operation": "real_browser.open",
                "arguments": {"url": url},
            },
            {
                "capability": "sentinel_loop",
                "operation": "finish",
                "arguments": {"answer": "Opened governed SQLite documentation."},
            },
        ]
    )
    result = run_canonical_product_mission(
        objective="Open a governed browser page.",
        workspace_root=workspace,
        model_client=model,
        provider_model="scripted-local/model",
        kernel=kernel,
        session_id=f"c5_physical_browser_site_scope_{stable_hash(url)[:12]}",
        capability_graph=build_workspace_browser_readonly_capability_graph(),
        browser_readonly_backend=backend,
        granted_authorities=("workspace_read", "browser_read", "none"),
    )
    return result, engine
