"""Local tests for the interactive exploration read-only harness.

Tests the new exploration loop WITHOUT any provider calls.
Uses SequenceSelfExplorationModelClient for deterministic outputs.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from sentinel.operator.self_exploration_read_only import (
    ReadOnlyPolicyViolation,
    ReadOnlyRepositorySnapshot,
    SelfExplorationModelCall,
    SelfExplorationPolicy,
    SequenceSelfExplorationModelClient,
)
from sentinel.operator.interactive_exploration_read_only import (
    EvidenceCatalogEntry,
    ExplorationBudgetStatus,
    ExplorationDecisionJournal,
    ExplorationState,
    ExplorationTool,
    InteractiveExplorationRunner,
    ReadOnlyExplorationLoop,
    SnapshotSearchIndex,
    build_exploration_turn_prompt,
    execute_snapshot_tool,
    interactive_policy_hash,
    interactive_safe_policy,
    parse_action_json,
    reject_unsafe_visible_report,
    run_smoke_a,
    run_smoke_b,
    validate_action,
)


# ---------------------------------------------------------------------------
# parse_action_json tests
# ---------------------------------------------------------------------------


class TestParseActionJson:
    def test_valid_json(self):
        text = '{"action": "list_directory", "target": ".", "parameters": {}}'
        parsed, err = parse_action_json(text)
        assert parsed is not None
        assert err is None
        assert parsed["action"] == "list_directory"

    def test_json_with_surrounding_prose_rejected(self):
        text = 'Here is my action:\n{"action": "search_text", "target": "MissionKernel", "parameters": {}}\nDone.'
        parsed, err = parse_action_json(text)
        assert parsed is None
        assert err == "JSON_MUST_BE_EXACT_OBJECT"

    def test_json_in_code_block_rejected(self):
        text = '```json\n{"action": "read_file_segment", "target": "foo.py", "parameters": {"start_line": 1, "end_line": 50}}\n```'
        parsed, err = parse_action_json(text)
        assert parsed is None
        assert err == "JSON_MUST_BE_EXACT_OBJECT"

    def test_no_json(self):
        text = "I think we should look at the kernel module."
        parsed, err = parse_action_json(text)
        assert parsed is None
        assert err == "JSON_MUST_BE_EXACT_OBJECT"

    def test_invalid_json(self):
        text = '{"action": "list_directory", "target": '
        parsed, err = parse_action_json(text)
        assert parsed is None

    def test_empty_string(self):
        parsed, err = parse_action_json("")
        assert parsed is None


# ---------------------------------------------------------------------------
# validate_action tests
# ---------------------------------------------------------------------------


class TestValidateAction:
    def test_valid_action(self):
        parsed = {"action": "list_directory", "target": ".", "parameters": {}}
        err, journal = validate_action(parsed)
        assert err is None

    def test_invalid_action(self):
        parsed = {"action": "delete_everything", "target": "/", "parameters": {}}
        err, journal = validate_action(parsed)
        assert err is not None
        assert "INVALID_ACTION" in err

    def test_missing_action(self):
        parsed = {"target": ".", "parameters": {}}
        err, journal = validate_action(parsed)
        assert err is not None

    def test_path_traversal_blocked(self):
        parsed = {"action": "read_file_segment", "target": "../../etc/passwd", "parameters": {}}
        err, journal = validate_action(parsed)
        assert err is not None
        assert "PATH_TRAVERSAL" in err

    @pytest.mark.parametrize(
        "target",
        [
            "C:\\Users\\youcef cheriet\\.env",
            "\\\\server\\share\\secret.txt",
            "sentinel-control\\..\\..\\secret.txt",
            "sentinel-control/services/..\\..\\secret.txt",
        ],
    )
    def test_windows_path_traversal_blocked(self, target):
        parsed = {"action": "read_file_segment", "target": target, "parameters": {}}

        err, journal = validate_action(parsed)

        assert err is not None
        assert "PATH_TRAVERSAL" in err

    def test_target_too_long(self):
        parsed = {"action": "search_text", "target": "x" * 600, "parameters": {}}
        err, journal = validate_action(parsed)
        assert err is not None
        assert "TOO_LONG" in err

    def test_partial_journal_does_not_block_action(self):
        """Critical: partial journal should NOT block a safe read-only action."""
        parsed = {
            "action": "list_directory",
            "target": ".",
            "parameters": {},
            # Missing all journal fields
        }
        err, journal = validate_action(parsed)
        assert err is None  # Action is valid!
        assert journal.journal_quality == "MINIMAL"

    def test_complete_journal(self):
        parsed = {
            "action": "search_text",
            "target": "MissionKernel",
            "parameters": {},
            "decision_summary": "Looking for the central orchestrator",
            "current_state": "initial exploration",
            "facts_confirmed": ["README exists"],
            "active_hypotheses": ["H1: MissionKernel is central"],
            "expected_result": "Find MissionKernel class definition",
        }
        err, journal = validate_action(parsed)
        assert err is None
        assert journal.journal_quality == "COMPLETE"
        assert journal.decision_summary == "Looking for the central orchestrator"

    def test_unknown_field_rejected(self):
        parsed = {
            "action": "list_directory",
            "target": ".",
            "parameters": {},
            "unexpected": "not allowed",
        }
        err, journal = validate_action(parsed)
        assert err == "UNKNOWN_FIELDS:unexpected"

    def test_journal_raw_provider_material_rejected(self):
        parsed = {
            "action": "list_directory",
            "target": ".",
            "parameters": {},
            "decision_summary": "raw_prompt should never persist",
        }

        err, journal = validate_action(parsed)

        assert err == "UNSAFE_JOURNAL_FIELD"
        assert journal.decision_summary == ""

    def test_journal_truncation(self):
        parsed = {
            "action": "list_directory",
            "target": ".",
            "parameters": {},
            "decision_summary": "x" * 2000,
        }
        err, journal = validate_action(parsed)
        assert err is None
        assert len(journal.decision_summary) == 1500


# ---------------------------------------------------------------------------
# ExplorationState tests
# ---------------------------------------------------------------------------


class TestExplorationState:
    def test_add_evidence(self):
        state = ExplorationState()
        ref = state.add_evidence(
            turn=1, action="list_directory", target=".",
            summary="Root listing", content="file1\nfile2",
        )
        assert ref == "E1"
        assert len(state.evidence_catalog) == 1

    def test_evidence_catalog_max(self):
        state = ExplorationState()
        for i in range(65):
            state.add_evidence(turn=i, action="search", target=f"q{i}", summary=f"s{i}", content=f"c{i}")
        assert len(state.evidence_catalog) == 60  # MAX_EVIDENCE_CATALOG_ENTRIES

    def test_update_from_journal_productive(self):
        state = ExplorationState()
        journal = ExplorationDecisionJournal(
            facts_confirmed=["MissionKernel exists in kernel.py"],
            active_hypotheses=["H1: MissionKernel is the dispatcher"],
        )
        changed = state.update_from_journal(journal)
        assert changed is True
        assert state.nonproductive_streak == 0
        assert len(state.facts_confirmed) == 1

    def test_update_from_journal_nonproductive(self):
        state = ExplorationState()
        journal = ExplorationDecisionJournal()
        changed = state.update_from_journal(journal)
        assert changed is False
        assert state.nonproductive_streak == 1
        state.update_from_journal(journal)
        assert state.nonproductive_streak == 2

    def test_duplicate_read_detection(self):
        state = ExplorationState()
        assert state.check_duplicate_read("foo.py", 1, 50) is False
        assert state.check_duplicate_read("foo.py", 1, 50) is False
        assert state.check_duplicate_read("foo.py", 1, 50) is False
        assert state.check_duplicate_read("foo.py", 1, 50) is True  # 4th time blocked

    def test_duplicate_read_different_range_allowed(self):
        state = ExplorationState()
        for _ in range(3):
            state.check_duplicate_read("foo.py", 1, 50)
        assert state.check_duplicate_read("foo.py", 51, 100) is False  # different range

    def test_duplicate_evidence_is_not_novel(self):
        state = ExplorationState()

        ref1 = state.add_evidence(
            turn=1,
            action="list_directory",
            target="sentinel-control/services/sentinel-core/sentinel",
            summary="root",
            content="[FILE] cli.py\n[DIR] operator",
        )
        ref2 = state.add_evidence(
            turn=2,
            action="list_directory",
            target="sentinel-control/services/sentinel-core/sentinel",
            summary="root again",
            content="[FILE] cli.py\n[DIR] operator",
        )

        assert ref1 == "E1"
        assert ref2 == "E2"
        assert state.evidence_catalog[0].novelty_status == "NOVEL"
        assert state.evidence_catalog[1].novelty_status == "DUPLICATE_EVIDENCE"

    def test_finish_requires_generic_depth_gate(self):
        state = ExplorationState()
        state.add_evidence(
            turn=1,
            action="list_directory",
            target=".",
            summary="root only",
            content="[FILE] README.md\n[DIR] sentinel-control",
        )

        ready, missing = state.finish_depth_gate()

        assert ready is False
        assert "mission_lifecycle" in missing
        assert "execution_runtime" in missing

    def test_finish_depth_gate_passes_with_generic_evidence_categories(self):
        state = ExplorationState()
        evidence = [
            ("read_file_segment", "sentinel/__main__.py", "entrypoint calls CLI main"),
            ("read_file_segment", "sentinel/operator/kernel.py", "MissionKernel mission lifecycle"),
            ("read_file_segment", "sentinel/organs/authority.py", "authority gate permission"),
            ("read_file_segment", "sentinel/agent/runtime.py", "AgentRuntime PowerRuntime execute"),
            ("read_file_segment", "sentinel/telemetry/kernel.py", "TelemetryKernel certified mode"),
            ("read_file_segment", "sentinel/final_gate.py", "receipt FinalGate certificate"),
            ("read_file_segment", "sentinel/operator/replay.py", "replay store durable checkpoint"),
            ("read_file_segment", "sentinel/organs/browser/backend.py", "browser organ capability"),
        ]
        for turn, (action, target, content) in enumerate(evidence, start=1):
            state.add_evidence(
                turn=turn,
                action=action,
                target=target,
                summary=content,
                content=content,
            )

        ready, missing = state.finish_depth_gate()

        assert ready is True
        assert missing == []


# ---------------------------------------------------------------------------
# SnapshotSearchIndex tests (using a minimal mock snapshot)
# ---------------------------------------------------------------------------


def _interactive_policy() -> SelfExplorationPolicy:
    return SelfExplorationPolicy(
        base_url="http://localhost:9999",
        max_model_calls=28,
        max_files_read=120,
        max_bytes_read=500_000,
        max_output_tokens_per_call=10_000,
        max_total_tokens=350_000,
        max_duration_seconds=900.0,
    )


def _make_test_snapshot(tmp_path: Path) -> ReadOnlyRepositorySnapshot:
    """Create a minimal test snapshot with a few files."""
    (tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "operator").mkdir(parents=True)
    kernel = tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "operator" / "kernel.py"
    kernel.write_text(
        "class MissionKernel:\n"
        "    def __init__(self):\n"
        "        self.state = 'idle'\n"
        "\n"
        "    def run(self):\n"
        "        self.state = 'running'\n"
        "        return AgentRuntime()\n"
        "\n"
        "class AgentRuntime:\n"
        "    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "__main__.py").write_text(
        "from sentinel.cli import main\n",
        encoding="utf-8",
    )
    (tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "organs").mkdir(parents=True)
    (tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "organs" / "authority.py").write_text(
        "class MissionAuthorityEnvelope: pass\nclass Gate: pass\n",
        encoding="utf-8",
    )
    (tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "agent").mkdir(parents=True)
    (tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "agent" / "runtime.py").write_text(
        "class AgentRuntime: pass\nclass PowerRuntime: pass\n",
        encoding="utf-8",
    )
    (tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "telemetry").mkdir(parents=True)
    (tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "telemetry" / "kernel.py").write_text(
        "class TelemetryKernel: pass\n",
        encoding="utf-8",
    )
    (tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "final_gate.py").write_text(
        "class FinalGate: pass\nclass Receipt: pass\n",
        encoding="utf-8",
    )
    (tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "operator" / "replay.py").write_text(
        "class MissionReplayBuilder: pass\nclass DurableStore: pass\n",
        encoding="utf-8",
    )
    (tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "organs" / "browser").mkdir(parents=True)
    (tmp_path / "sentinel-control" / "services" / "sentinel-core" / "sentinel" / "organs" / "browser" / "backend.py").write_text(
        "class BrowserCapability: pass\n",
        encoding="utf-8",
    )
    (tmp_path / "sentinel-control" / "services" / "sentinel-core" / "tests").mkdir(parents=True)
    test_file = tmp_path / "sentinel-control" / "services" / "sentinel-core" / "tests" / "test_kernel.py"
    test_file.write_text(
        "def test_mission_kernel():\n"
        "    from sentinel.operator.kernel import MissionKernel\n"
        "    mk = MissionKernel()\n"
        "    assert mk.state == 'idle'\n",
        encoding="utf-8",
    )
    (tmp_path / "sentinel-control" / "pyproject.toml").write_text("[project]\nname = 'sentinel'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Sentinel\nAI Agent Platform\n", encoding="utf-8")

    policy = _interactive_policy()
    return ReadOnlyRepositorySnapshot.freeze(repo_root=tmp_path, policy=policy)


def _depth_gate_outputs() -> list[str]:
    """Return generic read actions covering the required finish-depth categories."""
    return [
        json.dumps({
            "action": "read_file_segment", "target": "sentinel-control/services/sentinel-core/sentinel/__main__.py",
            "parameters": {"start_line": 0, "end_line": 50},
            "decision_summary": "Inspect entrypoint", "evidence_refs": [],
            "current_state": "entrypoint", "facts_confirmed": [],
            "active_hypotheses": [], "confidence": 0.6,
        }),
        json.dumps({
            "action": "read_file_segment", "target": "sentinel-control/services/sentinel-core/sentinel/operator/kernel.py",
            "parameters": {"start_line": 0, "end_line": 80},
            "decision_summary": "Inspect mission lifecycle", "evidence_refs": [],
            "current_state": "mission lifecycle", "facts_confirmed": [],
            "active_hypotheses": [], "confidence": 0.6,
        }),
        json.dumps({
            "action": "read_file_segment", "target": "sentinel-control/services/sentinel-core/sentinel/organs/authority.py",
            "parameters": {"start_line": 0, "end_line": 80},
            "decision_summary": "Inspect authority path", "evidence_refs": [],
            "current_state": "authority", "facts_confirmed": [],
            "active_hypotheses": [], "confidence": 0.6,
        }),
        json.dumps({
            "action": "read_file_segment", "target": "sentinel-control/services/sentinel-core/sentinel/agent/runtime.py",
            "parameters": {"start_line": 0, "end_line": 80},
            "decision_summary": "Inspect execution runtime", "evidence_refs": [],
            "current_state": "runtime", "facts_confirmed": [],
            "active_hypotheses": [], "confidence": 0.6,
        }),
        json.dumps({
            "action": "search_text", "target": "TelemetryKernel", "parameters": {},
            "decision_summary": "Inspect telemetry path", "evidence_refs": [],
            "current_state": "telemetry", "facts_confirmed": [],
            "active_hypotheses": [], "confidence": 0.6,
        }),
        json.dumps({
            "action": "search_text", "target": "FinalGate", "parameters": {},
            "decision_summary": "Inspect proof path", "evidence_refs": [],
            "current_state": "proof", "facts_confirmed": [],
            "active_hypotheses": [], "confidence": 0.6,
        }),
        json.dumps({
            "action": "search_text", "target": "MissionReplayBuilder", "parameters": {},
            "decision_summary": "Inspect replay persistence path", "evidence_refs": [],
            "current_state": "replay", "facts_confirmed": [],
            "active_hypotheses": [], "confidence": 0.6,
        }),
        json.dumps({
            "action": "list_directory", "target": "sentinel-control/services/sentinel-core/sentinel/organs/browser",
            "parameters": {},
            "decision_summary": "Inspect one capability path", "evidence_refs": [],
            "current_state": "capability", "facts_confirmed": [],
            "active_hypotheses": [], "confidence": 0.6,
        }),
    ]


class TestSnapshotSearchIndex:
    def test_build_index(self, tmp_path):
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        assert index.file_count > 0

    def test_search_text(self, tmp_path):
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        results = index.search_text("MissionKernel")
        assert len(results) > 0
        assert any("MissionKernel" in r["content"] for r in results)

    def test_search_symbol(self, tmp_path):
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        results = index.search_symbol("AgentRuntime")
        assert len(results) > 0

    def test_list_directory(self, tmp_path):
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        entries = index.list_directory(".")
        assert len(entries) > 0
        paths = [e["path"] for e in entries]
        assert any("sentinel-control" in p for p in paths)

    def test_read_file_segment(self, tmp_path):
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        # Find an accessible file
        accessible = [item.path for item in snapshot.inventory if item.stage_a_accessible]
        if accessible:
            content = index.read_file_segment(accessible[0], 1, 10)
            assert content is not None

    def test_read_nonexistent_file(self, tmp_path):
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        content = index.read_file_segment("does_not_exist.py", 1, 10)
        assert content is None

    def test_secret_like_allowed_file_is_not_indexed_or_exposed(self, tmp_path):
        path = (
            tmp_path
            / "sentinel-control"
            / "services"
            / "sentinel-core"
            / "sentinel"
            / "operator"
            / "benign.py"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Authorization: Bearer abcdefghijklmnop1234567890\n", encoding="utf-8")
        snapshot = ReadOnlyRepositorySnapshot.freeze(repo_root=tmp_path, policy=_interactive_policy())
        index = SnapshotSearchIndex(snapshot)

        rel = "sentinel-control/services/sentinel-core/sentinel/operator/benign.py"
        assert index.get_file_content(rel) is None
        assert not index.search_text("Authorization")

    def test_stage_b_truth_docs_are_not_indexed_during_exploration(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Sentinel truth doc\nMissionKernel roadmap claim\n", encoding="utf-8")
        snapshot = _make_test_snapshot(tmp_path)
        assert snapshot.can_read("README.md", stage="B")
        assert not snapshot.can_read("README.md", stage="A")

        index = SnapshotSearchIndex(snapshot)

        assert index.get_file_content("README.md") is None
        assert not any(result["file"] == "README.md" for result in index.search_text("MissionKernel"))


# ---------------------------------------------------------------------------
# execute_snapshot_tool tests
# ---------------------------------------------------------------------------


class TestExecuteSnapshotTool:
    def test_list_directory(self, tmp_path):
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        state = ExplorationState()
        budget = ExplorationBudgetStatus()
        obs, obs_bytes, count = execute_snapshot_tool(
            ExplorationTool.LIST_DIRECTORY, ".", {},
            search_index=index, snapshot=snapshot, state=state, budget=budget,
        )
        assert obs_bytes > 0
        assert count > 0

    def test_search_text(self, tmp_path):
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        state = ExplorationState()
        budget = ExplorationBudgetStatus()
        obs, obs_bytes, count = execute_snapshot_tool(
            ExplorationTool.SEARCH_TEXT, "MissionKernel", {},
            search_index=index, snapshot=snapshot, state=state, budget=budget,
        )
        assert count > 0
        assert "MissionKernel" in obs

    def test_finish_exploration(self, tmp_path):
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        state = ExplorationState()
        budget = ExplorationBudgetStatus()
        obs, obs_bytes, count = execute_snapshot_tool(
            ExplorationTool.FINISH_EXPLORATION, "done", {},
            search_index=index, snapshot=snapshot, state=state, budget=budget,
        )
        assert obs == "EXPLORATION_COMPLETE"

    def test_inspect_git_metadata(self, tmp_path):
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        state = ExplorationState()
        budget = ExplorationBudgetStatus()
        obs, obs_bytes, count = execute_snapshot_tool(
            ExplorationTool.INSPECT_GIT_METADATA, ".", {},
            search_index=index, snapshot=snapshot, state=state, budget=budget,
        )
        parsed = json.loads(obs)
        assert "inventory_count" in parsed

    def test_unknown_tool_raises(self, tmp_path):
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        state = ExplorationState()
        budget = ExplorationBudgetStatus()
        with pytest.raises(ReadOnlyPolicyViolation):
            execute_snapshot_tool(
                "write_file", "evil.py", {},  # type: ignore
                search_index=index, snapshot=snapshot, state=state, budget=budget,
            )


# ---------------------------------------------------------------------------
# Smoke test tests (using SequenceSelfExplorationModelClient)
# ---------------------------------------------------------------------------


class TestSmokeA:
    def test_smoke_a_passes(self):
        client = SequenceSelfExplorationModelClient([
            "Sentinel\nAn AI agent platform\nImpressive\ndeepseek-v4-pro\nSMOKE_COMPLETE"
        ])
        policy = SelfExplorationPolicy(base_url="http://localhost:9999")
        passed, result = run_smoke_a(client, policy, "test-mission")
        assert passed is True
        assert result["contains_marker"] is True

    def test_smoke_a_fails_empty(self):
        client = SequenceSelfExplorationModelClient([""])
        policy = SelfExplorationPolicy(base_url="http://localhost:9999")
        passed, result = run_smoke_a(client, policy, "test-mission")
        assert passed is False

    def test_smoke_a_fails_no_marker(self):
        client = SequenceSelfExplorationModelClient([
            "Sentinel\nAn AI agent platform\nImpressive\ndeepseek\nDone"
        ])
        policy = SelfExplorationPolicy(base_url="http://localhost:9999")
        passed, result = run_smoke_a(client, policy, "test-mission")
        assert passed is False


class TestSmokeB:
    def test_smoke_b_passes(self, tmp_path):
        action_json = json.dumps({
            "action": "list_directory",
            "target": ".",
            "parameters": {},
            "decision_summary": "Initial root scan",
            "evidence_refs": [],
            "current_state": "initial",
            "facts_confirmed": [],
            "active_hypotheses": [],
            "confidence": 0.5,
        })
        client = SequenceSelfExplorationModelClient([action_json])
        policy = SelfExplorationPolicy(
            base_url="http://localhost:9999",
            max_model_calls=28,
            max_files_read=120,
            max_bytes_read=500_000,
            max_output_tokens_per_call=10_000,
            max_total_tokens=350_000,
        )
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        state = ExplorationState()
        budget = ExplorationBudgetStatus()
        passed, result = run_smoke_b(client, policy, "test-mission", index, snapshot, state, budget)
        assert passed is True
        assert result["json_valid"] is True
        assert result["action_valid"] is True

    def test_smoke_b_fails_bad_json(self, tmp_path):
        client = SequenceSelfExplorationModelClient(["I want to explore the repository."])
        policy = SelfExplorationPolicy(
            base_url="http://localhost:9999",
            max_model_calls=28,
            max_files_read=120,
            max_bytes_read=500_000,
            max_output_tokens_per_call=10_000,
            max_total_tokens=350_000,
        )
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        state = ExplorationState()
        budget = ExplorationBudgetStatus()
        passed, result = run_smoke_b(client, policy, "test-mission", index, snapshot, state, budget)
        assert passed is False
        assert result["json_valid"] is False

    def test_smoke_b_rejects_wrong_action(self, tmp_path):
        action_json = json.dumps({
            "action": "search_text",
            "target": "MissionKernel",
            "parameters": {},
            "decision_summary": "Wrong first action",
            "evidence_refs": [],
            "current_state": "initial",
            "facts_confirmed": [],
            "active_hypotheses": [],
            "confidence": 0.5,
        })
        client = SequenceSelfExplorationModelClient([action_json])
        policy = _interactive_policy()
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        state = ExplorationState()
        budget = ExplorationBudgetStatus()
        passed, result = run_smoke_b(client, policy, "test-mission", index, snapshot, state, budget)
        assert passed is False
        assert result["action_valid"] is False
        assert result["action_error"] == "SMOKE_B_WRONG_ACTION"

    def test_smoke_b_rejects_unknown_field(self, tmp_path):
        action_json = json.dumps({
            "action": "list_directory",
            "target": ".",
            "parameters": {},
            "decision_summary": "Initial root scan",
            "evidence_refs": [],
            "current_state": "initial",
            "facts_confirmed": [],
            "active_hypotheses": [],
            "confidence": 0.5,
            "provider_override": "never",
        })
        client = SequenceSelfExplorationModelClient([action_json])
        policy = _interactive_policy()
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        state = ExplorationState()
        budget = ExplorationBudgetStatus()
        passed, result = run_smoke_b(client, policy, "test-mission", index, snapshot, state, budget)
        assert passed is False
        assert result["action_valid"] is False
        assert result["action_error"] == "UNKNOWN_FIELDS:provider_override"


class TestVisibleReportSafety:
    def test_stage_report_rejects_secret_like_text(self):
        with pytest.raises(RuntimeError, match="unsafe_visible_report"):
            reject_unsafe_visible_report(
                "Finding: Authorization: Bearer abcdefghijklmnop should never persist",
                stage="stage_a",
            )

    def test_stage_report_rejects_raw_provider_material_marker(self):
        with pytest.raises(RuntimeError, match="unsafe_visible_report"):
            reject_unsafe_visible_report(
                "This report includes raw_prompt and provider_response material.",
                stage="stage_b",
            )


# ---------------------------------------------------------------------------
# Exploration loop integration test
# ---------------------------------------------------------------------------


class TestExplorationLoop:
    def test_three_turn_exploration(self, tmp_path):
        """Model does: list_directory → search_text → finish_exploration."""
        outputs = [
            json.dumps({
                "action": "list_directory", "target": ".", "parameters": {},
                "decision_summary": "Scan root", "evidence_refs": [],
                "current_state": "starting", "facts_confirmed": [],
                "active_hypotheses": [], "confidence": 0.5,
            }),
            json.dumps({
                "action": "search_text", "target": "MissionKernel", "parameters": {},
                "decision_summary": "Find central class", "evidence_refs": ["E1"],
                "current_state": "searching", "facts_confirmed": ["Root has sentinel-control"],
                "active_hypotheses": ["H1: MissionKernel is central"], "confidence": 0.6,
            }),
            *_depth_gate_outputs(),
            json.dumps({
                "action": "finish_exploration", "target": "done", "parameters": {},
                "decision_summary": "Enough evidence", "evidence_refs": ["E1", "E2"],
                "current_state": "finishing", "facts_confirmed": ["MissionKernel exists"],
                "active_hypotheses": ["H1: MissionKernel is central"], "confidence": 0.8,
            }),
        ]
        client = SequenceSelfExplorationModelClient(outputs)
        policy = SelfExplorationPolicy(
            base_url="http://localhost:9999",
            max_model_calls=28,
            max_files_read=120,
            max_bytes_read=500_000,
            max_output_tokens_per_call=10_000,
            max_total_tokens=350_000,
        )
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        loop = ReadOnlyExplorationLoop(
            model_client=client,
            policy=policy,
            snapshot=snapshot,
            search_index=index,
            mission_id="test-loop",
            output_root=output_dir,
        )
        final_state, trajectory = loop.run()

        assert len(trajectory) == 11
        assert trajectory[0].action == "list_directory"
        assert trajectory[1].action == "search_text"
        assert trajectory[-1].action == "finish_exploration"
        assert trajectory[-1].validation_success is True
        assert len(final_state.evidence_catalog) >= 2
        assert "MissionKernel exists" in final_state.facts_confirmed

        # Trajectory file written
        traj_file = output_dir / "exploration_trajectory.jsonl"
        assert traj_file.exists()
        lines = traj_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 11

    def test_superficial_finish_is_blocked_by_depth_gate(self, tmp_path):
        outputs = [
            json.dumps({
                "action": "finish_exploration", "target": "done", "parameters": {},
            }),
            *_depth_gate_outputs(),
            json.dumps({
                "action": "finish_exploration", "target": "done", "parameters": {},
            }),
        ]
        client = SequenceSelfExplorationModelClient(outputs)
        policy = SelfExplorationPolicy(
            base_url="http://localhost:9999",
            max_model_calls=28,
            max_files_read=120,
            max_bytes_read=500_000,
            max_output_tokens_per_call=10_000,
            max_total_tokens=350_000,
        )
        snapshot = _make_test_snapshot(tmp_path)
        index = SnapshotSearchIndex(snapshot)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        loop = ReadOnlyExplorationLoop(
            model_client=client, policy=policy, snapshot=snapshot,
            search_index=index, mission_id="test-fail", output_root=output_dir,
        )
        final_state, trajectory = loop.run()

        assert trajectory[0].action == "finish_exploration"
        assert trajectory[0].validation_success is False
        assert trajectory[0].action_blocked_reason.startswith("DEPTH_GATE_BLOCKED:")
        assert trajectory[-1].action == "finish_exploration"
        assert trajectory[-1].validation_success is True


class TestInteractiveExplorationRunner:
    def test_stage_b_empty_persists_safe_call_metadata_and_counts_attempt(self, tmp_path):
        smoke_b = json.dumps({
            "action": "list_directory",
            "target": ".",
            "parameters": {},
            "decision_summary": "Initial root scan",
            "evidence_refs": [],
            "current_state": "initial",
            "facts_confirmed": [],
            "active_hypotheses": [],
            "confidence": 0.5,
        })
        finish = json.dumps({
            "action": "finish_exploration",
            "target": "done",
            "parameters": {},
            "decision_summary": "Enough evidence for the smoke-sized run.",
            "evidence_refs": [],
            "current_state": "finished",
            "facts_confirmed": ["Root was listed"],
            "active_hypotheses": [],
            "confidence": 0.8,
        })
        client = SequenceSelfExplorationModelClient([
            "Sentinel\nA governed local agent system\nPromising\ndeepseek-v4-pro\nSMOKE_COMPLETE",
            smoke_b,
            *_depth_gate_outputs(),
            finish,
            "Stage A visible report with E1 evidence.",
            "",
        ])
        policy = _interactive_policy()
        policy.experiment_version = "REAL_MODEL_SENTINEL_INTERACTIVE_EXPLORATION_READ_ONLY_V1"
        _make_test_snapshot(tmp_path)
        output_dir = tmp_path / "interactive-output"
        runner = InteractiveExplorationRunner(policy=policy, model_client=client)

        report = runner.run(
            repo_root=tmp_path,
            output_root=output_dir,
            expected_policy_hash=interactive_policy_hash(policy),
        )

        assert report.verdict == "STAGE_B_EMPTY"
        assert report.total_model_calls == 13
        stage_a = json.loads((output_dir / "stage_a_call_result.json").read_text(encoding="utf-8"))
        stage_b = json.loads((output_dir / "stage_b_call_result.json").read_text(encoding="utf-8"))
        assert stage_a["visible_text_length"] > 0
        assert stage_b["visible_text_length"] == 0
        assert "visible_text" not in stage_a
        assert "visible_text" not in stage_b
        assert (output_dir / "final_report.json").exists()


# ---------------------------------------------------------------------------
# Prompt builder tests
# ---------------------------------------------------------------------------


class TestPromptBuilder:
    def test_turn_prompt_contains_required_sections(self):
        state = ExplorationState()
        state.facts_confirmed = ["MissionKernel exists"]
        state.active_hypotheses = ["H1: kernel is central"]
        state.add_evidence(turn=1, action="list", target=".", summary="root listing", content="files")
        budget = ExplorationBudgetStatus(turns_remaining=20)
        prompt = build_exploration_turn_prompt(
            mission_id="test", turn=2, state=state, budget=budget, recent_turns=[],
        )
        assert "EXPLORATION STATE" in prompt
        assert "EVIDENCE CATALOG" in prompt
        assert "BUDGET" in prompt
        assert "MissionKernel exists" in prompt
        assert "H1:" in prompt
        assert "E1" in prompt


# ---------------------------------------------------------------------------
# Decision journal quality tests
# ---------------------------------------------------------------------------


class TestDecisionJournalQuality:
    def test_minimal(self):
        journal = ExplorationDecisionJournal()
        assert journal.journal_quality == "MINIMAL"

    def test_partial(self):
        journal = ExplorationDecisionJournal(
            decision_summary="Looking at root",
            current_state="starting",
        )
        assert journal.journal_quality == "PARTIAL"

    def test_complete(self):
        journal = ExplorationDecisionJournal(
            decision_summary="Search for kernel",
            current_state="searching",
            facts_confirmed=["Root exists"],
            active_hypotheses=["H1: kernel central"],
            expected_result="Find MissionKernel",
        )
        assert journal.journal_quality == "COMPLETE"


class TestInteractivePolicyFreeze:
    def test_policy_hash_includes_interactive_version_and_budgets(self):
        policy = _interactive_policy()
        policy.experiment_version = "REAL_MODEL_SENTINEL_INTERACTIVE_EXPLORATION_READ_ONLY_V1"
        safe = interactive_safe_policy(policy)
        assert safe["experiment_version"] == "REAL_MODEL_SENTINEL_INTERACTIVE_EXPLORATION_READ_ONLY_V1"
        assert safe["interactive_experiment_version"] == "REAL_MODEL_SENTINEL_INTERACTIVE_EXPLORATION_READ_ONLY_V1"
        assert safe["interactive_budgets"]["max_total_model_calls"] == 28
        assert safe["interactive_budgets"]["max_exploration_turns"] == 24
        changed = _interactive_policy()
        changed.experiment_version = "OTHER"
        assert interactive_policy_hash(policy) != interactive_policy_hash(changed)
