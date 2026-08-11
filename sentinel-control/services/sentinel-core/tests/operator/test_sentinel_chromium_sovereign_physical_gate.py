from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.real_browser_control_runtime import RealBrowserEngineElement, RealBrowserEngineSnapshot
from sentinel.operator.sovereign_browser_physical_gate import (
    BrowserProcessSnapshot,
    run_owned_stage_timeout_probe,
    run_sentinel_chromium_sovereign_physical_gate,
    summarize_sentinel_chromium_sovereign_boundary_probes,
)


class GateFakeEngine:
    browser_backend_id = "sentinel_chromium"
    session_manager_backend_kind = "sentinel_chromium"

    def __init__(self, *, capture_root: Path, close_raises: bool = False, leak_profile: bool = False) -> None:
        self.capture_root = capture_root
        self.close_raises = close_raises
        self.leak_profile = leak_profile
        self.open_count = 0
        self.observe_count = 0
        self.close_count = 0
        self.bound_authority: Any | None = None
        self.bound_root_session_id = ""

    @property
    def safe_url_origin_hash(self) -> str:
        return stable_hash({"scheme": "https", "host": "example.com", "port": None})

    def bind_authority(self, authority: Any) -> None:
        self.bound_authority = authority

    def bind_root_session_id(self, root_session_id: str) -> None:
        self.bound_root_session_id = root_session_id

    def open(self) -> RealBrowserEngineSnapshot:
        self.open_count += 1
        if self.leak_profile:
            profile = self.capture_root / "browser_session" / "profile"
            profile.mkdir(parents=True, exist_ok=True)
            (profile / "LOCK").write_text("owned test profile", encoding="utf-8")
        return self._snapshot("open")

    def observe(self) -> RealBrowserEngineSnapshot:
        self.observe_count += 1
        return self._snapshot("observe")

    def close(self) -> None:
        self.close_count += 1
        if self.close_raises:
            raise RuntimeError("close failed with sensitive path C:/do-not-persist")
        if self.leak_profile:
            return

    def _snapshot(self, stage: str) -> RealBrowserEngineSnapshot:
        return RealBrowserEngineSnapshot(
            page_title=f"Example {stage}",
            state_hash=stable_hash({"stage": stage, "open_count": self.open_count, "observe_count": self.observe_count}),
            elements=(
                RealBrowserEngineElement(
                    ref="link:docs",
                    role="link",
                    name="Docs",
                    text_preview="Docs",
                ),
            ),
        )


def test_sovereign_physical_gate_requires_close_completion_and_baseline_restore(tmp_path: Path) -> None:
    result = run_sentinel_chromium_sovereign_physical_gate(
        capture_root=tmp_path / "gate",
        target_url="https://example.com/",
        cycles=5,
        engine_factory=lambda cycle_root, _target_url, _timeout_ms: GateFakeEngine(capture_root=cycle_root),
        process_snapshotter=lambda: BrowserProcessSnapshot(identity_hashes=()),
    )

    assert result["verdict"] == "SOVEREIGN_PHYSICAL_GATE_PASSED"
    assert result["gates"]["launches"] == "5/5"
    assert result["gates"]["usable_context_page_observation"] == "5/5"
    assert result["gates"]["actual_backend_id"] == "sentinel_chromium"
    assert result["gates"]["cloak_dependency"] is False
    assert result["gates"]["close_completed"] == "5/5"
    assert result["gates"]["process_baseline_restored"] == "5/5"
    assert result["gates"]["profile_material_persisted"] is False
    assert result["provider_calls"] == 0
    assert result["product_browser_missions"] == 0
    assert all(cycle["close_completed"] is True for cycle in result["cycles"])


def test_sovereign_physical_gate_does_not_treat_close_called_as_close_completed(tmp_path: Path) -> None:
    result = run_sentinel_chromium_sovereign_physical_gate(
        capture_root=tmp_path / "gate",
        target_url="https://example.com/",
        cycles=1,
        engine_factory=lambda cycle_root, _target_url, _timeout_ms: GateFakeEngine(
            capture_root=cycle_root,
            close_raises=True,
        ),
        process_snapshotter=lambda: BrowserProcessSnapshot(identity_hashes=()),
    )

    assert result["verdict"] == "SOVEREIGN_PHYSICAL_GATE_FAILED"
    assert result["cycles"][0]["close_called"] is True
    assert result["cycles"][0]["close_completed"] is False
    assert result["cycles"][0]["failure_code"] == "sovereign_browser_close_failed"
    assert "do-not-persist" not in str(result)


def test_sovereign_physical_gate_marks_owned_profile_material_persistence(tmp_path: Path) -> None:
    result = run_sentinel_chromium_sovereign_physical_gate(
        capture_root=tmp_path / "gate",
        target_url="https://example.com/",
        cycles=1,
        engine_factory=lambda cycle_root, _target_url, _timeout_ms: GateFakeEngine(
            capture_root=cycle_root,
            leak_profile=True,
        ),
        process_snapshotter=lambda: BrowserProcessSnapshot(identity_hashes=()),
    )

    assert result["verdict"] == "SOVEREIGN_PHYSICAL_GATE_FAILED"
    assert result["cycles"][0]["profile_material_persisted"] is True
    assert result["gates"]["profile_material_persisted"] is True


def test_sovereign_physical_gate_fails_when_process_baseline_is_not_restored(tmp_path: Path) -> None:
    snapshots = [
        BrowserProcessSnapshot(identity_hashes=("baseline",)),
        BrowserProcessSnapshot(identity_hashes=("baseline", "survivor")),
    ]
    calls = {"count": 0}

    def _snapshotter() -> BrowserProcessSnapshot:
        calls["count"] += 1
        if calls["count"] <= len(snapshots):
            return snapshots[calls["count"] - 1]
        return snapshots[-1]

    result = run_sentinel_chromium_sovereign_physical_gate(
        capture_root=tmp_path / "gate",
        target_url="https://example.com/",
        cycles=1,
        engine_factory=lambda cycle_root, _target_url, _timeout_ms: GateFakeEngine(capture_root=cycle_root),
        process_snapshotter=_snapshotter,
    )

    assert result["verdict"] == "SOVEREIGN_PHYSICAL_GATE_FAILED"
    assert result["cycles"][0]["process_baseline_restored"] is False
    assert result["cycles"][0]["owned_process_survivor_count"] == 1


def test_owned_stage_timeout_probe_kills_child_tree_and_prevents_late_publication(tmp_path: Path) -> None:
    result = run_owned_stage_timeout_probe(stage="initial_navigation", capture_root=tmp_path / "timeout")

    assert result["stage"] == "initial_navigation"
    assert result["stage_started"] is True
    assert result["timed_out"] is True
    assert result["worker_terminated"] is True
    assert result["process_tree_killed"] is True
    assert result["late_publication_blocked"] is True
    assert result["terminal_receipt_count"] == 1
    assert "profile" not in str(result).lower()


def test_boundary_probe_summary_requires_each_required_boundary() -> None:
    summary = summarize_sentinel_chromium_sovereign_boundary_probes(
        same_origin_allowed=True,
        cross_origin_blocked=True,
        cross_origin_cleanup_completed=True,
        timeout_probes={
            "launch": {"worker_terminated": True, "process_tree_killed": True, "late_publication_blocked": True, "terminal_receipt_count": 1},
            "context": {"worker_terminated": True, "process_tree_killed": True, "late_publication_blocked": True, "terminal_receipt_count": 1},
            "navigation": {"worker_terminated": True, "process_tree_killed": True, "late_publication_blocked": True, "terminal_receipt_count": 1},
        },
    )

    assert summary["boundary_gate_passed"] is True
    assert summary["same_origin_allowed"] is True
    assert summary["redirect_cross_origin_blocked"] is True
    assert summary["timeout_launch"] is True
    assert summary["timeout_context"] is True
    assert summary["timeout_navigation"] is True


def test_boundary_probe_summary_fails_if_one_timeout_stage_is_missing() -> None:
    summary = summarize_sentinel_chromium_sovereign_boundary_probes(
        same_origin_allowed=True,
        cross_origin_blocked=True,
        cross_origin_cleanup_completed=True,
        timeout_probes={
            "launch": {"worker_terminated": True, "process_tree_killed": True, "late_publication_blocked": True, "terminal_receipt_count": 1},
            "context": {"worker_terminated": True, "process_tree_killed": True, "late_publication_blocked": True, "terminal_receipt_count": 1},
        },
    )

    assert summary["boundary_gate_passed"] is False
    assert summary["timeout_navigation"] is False
