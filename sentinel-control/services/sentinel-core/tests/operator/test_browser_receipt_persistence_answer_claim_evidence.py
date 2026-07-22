from __future__ import annotations

import json
from pathlib import Path

from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.browser_proof_index import (
    BrowserProofIndexBuilder,
    classify_browser_completion_truth,
    normalize_blind_evaluator_result,
    normalize_answer_claims,
    sanitize_public_evidence,
)
from sentinel.operator.live_run_evidence_sink import CrashSafeBoundedLiveRunEvidenceSink
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ProductActionKernelLoopDecisionClient,
    ProductActionKernelTaskLoopReplay,
    ProductActionKernelTaskLoopStatus,
)
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_browser_proof_index_resolves_browser_receipts_after_cleanup(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    sink = CrashSafeBoundedLiveRunEvidenceSink(evidence_root=tmp_path / "safe_evidence", run_id="browser_proof_index")

    result = host.run_product_action_kernel_task_loop(
        workspace_root=_workspace(tmp_path),
        session_id="browser-proof-index",
        mission_objective="Search a bounded fake browser page, extract evidence, verify it, summarize and finish.",
        decision_client=_browser_evidence_finish_client(),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=6,
        max_material_actions=4,
        evidence_sink=sink,
    )
    host.shutdown()

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED, result.blocked_reason
    index_path = host.kernel.store.run_root / "_browser_proof_index" / f"{result.loop_id}.json"
    sink_index_path = sink.run_dir / "browser_proof_index.json"

    assert index_path.exists()
    assert sink_index_path.exists()
    index = json.loads(index_path.read_text(encoding="utf-8"))
    sink_index = json.loads(sink_index_path.read_text(encoding="utf-8"))

    assert index["loop_id"] == result.loop_id
    assert index["browser_receipt_readable_count"] >= 3
    assert index["browser_receipt_missing_count"] == 0
    assert sink_index["browser_receipt_missing_count"] == 0
    material_entries = [entry for entry in index["material_browser_receipts"] if entry["browser_receipt_readable"]]
    assert {entry["operation"] for entry in material_entries} >= {
        "real_browser.search",
        "real_browser.extract_evidence",
        "real_browser.verify_extraction",
    }
    assert all(entry["product_receipt_ref"] for entry in material_entries)
    assert all(entry["browser_receipt_ref"] for entry in material_entries)
    assert all(entry["browser_receipt_location_ref"].startswith("mission_artifact:") for entry in material_entries)
    assert all("receipt_payload" in entry for entry in material_entries)

    rendered = json.dumps(index, sort_keys=True)
    assert str(tmp_path) not in rendered
    assert "raw_provider" not in rendered.lower()
    assert "raw_dom" not in rendered.lower()
    assert "cookie" not in rendered.lower()


def test_product_action_kernel_receipts_use_compact_physical_mapping_for_long_logical_refs(tmp_path: Path) -> None:
    long_root = tmp_path / "artifact_root"
    host = SentinelRuntimeHost(run_root=long_root / "runs").start().host

    result = host.run_product_action_kernel_task_loop(
        workspace_root=_workspace(tmp_path),
        session_id="compact-pak-receipts",
        mission_objective="Search a bounded fake browser page, extract evidence, verify it, summarize and finish.",
        decision_client=_browser_evidence_finish_client(),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=6,
        max_material_actions=4,
    )
    host.shutdown()

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED, result.blocked_reason
    for mission_id in result.mission_ids:
        mission_dir = host.kernel.store.mission_dir(mission_id)
        receipt_index = mission_dir / "_pak" / "index" / "r.json"
        assert receipt_index.exists()
        mapping = json.loads(receipt_index.read_text(encoding="utf-8"))
        assert mapping["schema_version"] == "product_action_kernel_artifact_index_v1"
        assert mapping["entries"]
        for logical_ref, entry in mapping["entries"].items():
            assert logical_ref.startswith("product_action_kernel_receipt_")
            assert entry["logical_ref"] == logical_ref
            assert entry["collection"] == "receipts"
            assert entry["physical_ref"]
            physical = mission_dir / entry["relative_path"]
            assert physical.exists()
            payload = json.loads(physical.read_text(encoding="utf-8"))
            assert payload["receipt_id"] == logical_ref
            assert str(physical).find("product_action_kernel_receipt_") == -1


def test_public_evidence_keeps_readable_provenance_without_secret_query_params() -> None:
    evidence = sanitize_public_evidence(
        {
            "evidence_id": "evidence:python-pathlib-glob",
            "source_url": "https://docs.python.org/3/library/pathlib.html?highlight=glob&token=secret-value",
            "source_title": "pathlib - Object-oriented filesystem paths",
            "source_origin": "https://docs.python.org",
            "excerpt": "Path.glob(pattern) glob the given relative pattern in the directory represented by this path.",
        }
    )

    assert evidence["normalized_public_url"] == "https://docs.python.org/3/library/pathlib.html?highlight=glob"
    assert evidence["source_title"] == "pathlib - Object-oriented filesystem paths"
    assert evidence["source_origin"] == "https://docs.python.org"
    assert "Path.glob" in evidence["bounded_excerpt"]
    assert "secret-value" not in json.dumps(evidence)
    assert evidence["digest"]
    assert evidence["evidence_human_readable"] is True
    assert evidence["source_identity_readable"] is True
    assert evidence["evidence_redaction_status"] == "readable"
    assert evidence["evidence_supports_claim_candidate"] is True


def test_public_evidence_marks_operation_only_or_fully_redacted_cards_unreadable() -> None:
    evidence = sanitize_public_evidence(
        {
            "evidence_id": "evidence:operation-only",
            "source_title": "real_browser.extract_evidence",
            "source_origin": "origin-hash:abcdef",
            "excerpt": "real_browser.extract_evidence status=completed typed_outcome=MATERIAL_RESULTS",
        }
    )

    assert evidence["evidence_human_readable"] is False
    assert evidence["source_identity_readable"] is False
    assert evidence["evidence_redaction_status"] == "unreadable"
    assert evidence["evidence_supports_claim_candidate"] is False


def test_public_evidence_redacts_actual_secret_values_without_topic_word_redaction() -> None:
    evidence = sanitize_public_evidence(
        {
            "evidence_id": "evidence:password-docs",
            "source_url": "https://docs.example.test/security/passwords.html",
            "source_title": "Password manager documentation",
            "source_origin": "https://docs.example.test",
            "excerpt": "This public page explains password managers and shows token=sk-1234567890abcdef1234567890abcdef as an example secret.",
        }
    )

    assert "password managers" in evidence["bounded_excerpt"]
    assert "token=" not in evidence["bounded_excerpt"]
    assert "[redacted-secret-like-value]" in evidence["bounded_excerpt"]
    assert evidence["evidence_redaction_status"] == "partially_redacted"
    assert evidence["evidence_human_readable"] is True


def test_answer_claim_candidates_separate_facts_inferences_unknowns_and_open_world_types() -> None:
    claims = normalize_answer_claims(
        [
            {
                "claim_id": "claim:glob-fact",
                "claim_type": "sourced_factual_claim",
                "text": "Path.glob accepts a pattern argument.",
                "evidence_refs": ["evidence:python-pathlib-glob"],
                "confidence": 0.94,
            },
            {
                "claim_id": "claim:useful-inference",
                "claim_type": "model_inference",
                "text": "Use recursive patterns carefully for large trees.",
                "evidence_refs": [],
                "confidence": 0.7,
            },
            {
                "claim_id": "claim:unknown-version",
                "claim_type": "declared_unknown",
                "text": "The exact Python minor version is unknown from the captured evidence.",
                "evidence_refs": [],
                "confidence": 1.0,
            },
            {
                "claim_id": "claim:future-kind",
                "claim_type": "model_proposed_semantic_relation",
                "text": "The model proposed a novel safe relation type.",
                "evidence_refs": ["evidence:python-pathlib-glob"],
                "confidence": 0.5,
            },
        ],
        evidence_ids={"evidence:python-pathlib-glob"},
    )

    assert claims["factual_supported_count"] == 1
    assert claims["factual_unsupported_count"] == 0
    assert claims["inference_count"] == 1
    assert claims["declared_unknown_count"] == 1
    assert claims["open_world_claim_type_count"] == 1
    assert claims["claims"][3]["claim_type"] == "model_proposed_semantic_relation"
    assert claims["claims"][1]["support_status"] == "inference_not_factual_claim"


def test_answer_claim_candidates_mark_missing_factual_refs_without_punishing_uncertainty() -> None:
    claims = normalize_answer_claims(
        [
            {
                "claim_type": "sourced_factual_claim",
                "text": "Path.glob follows symlinks in every case.",
                "evidence_refs": ["evidence:missing"],
            },
            {
                "claim_type": "uncertainty",
                "text": "The captured evidence does not establish symlink behavior.",
            },
        ],
        evidence_ids={"evidence:python-pathlib-glob"},
    )

    assert claims["factual_supported_count"] == 0
    assert claims["factual_unsupported_count"] == 1
    assert claims["uncertainty_count"] == 1
    assert claims["unsupported_claim_count"] == 1


def test_finish_after_grounded_summary_completes_without_reasking_model(tmp_path: Path) -> None:
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "pathlib glob", "engine_profile": "fake_product_search"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_evidence",
                params={"engine_profile": "fake_product_search"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.verify_extraction",
                params={"engine_profile": "fake_product_search"},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence", params={}),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "done"},
            ),
        ]
    )
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host

    result = host.run_product_action_kernel_task_loop(
        workspace_root=_workspace(tmp_path),
        session_id="finish-contract",
        mission_objective="Find documentation evidence and provide a useful answer.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=7,
        max_material_actions=4,
    )
    host.shutdown()

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED, result.blocked_reason
    assert client.call_count == 5
    final_context = client.contexts[-1]
    assert final_context["recoverable_decision_observations"] == []
    index_path = host.kernel.store.run_root / "_browser_proof_index" / f"{result.loop_id}.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["final_answer"]["answer_text"]
    assert index["answer_claims"]["factual_supported_count"] == 1


def test_honest_blocker_can_finish_without_fabricated_factual_claims(tmp_path: Path) -> None:
    client = ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "pathlib glob", "engine_profile": "fake_product_search"},
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={
                    "honest_blocker": {
                        "reason": "The browser body did not provide enough readable public evidence.",
                        "available_evidence_refs": [],
                        "missing_evidence": ["human-readable public source excerpt"],
                    }
                },
            ),
        ]
    )
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host

    result = host.run_product_action_kernel_task_loop(
        workspace_root=_workspace(tmp_path),
        session_id="honest-blocker-contract",
        mission_objective="Find documentation evidence and provide a useful answer.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=3,
        max_material_actions=1,
    )
    host.shutdown()

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED, result.blocked_reason
    index_path = host.kernel.store.run_root / "_browser_proof_index" / f"{result.loop_id}.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["honest_blocker"]["reason"]
    assert index["answer_claims"]["factual_supported_count"] == 0
    assert index["completion_truth"]["honest_blocker_present"] is True
    assert index["completion_truth"]["mission_objective_satisfied"] is False


def test_no_action_no_evidence_completion_truth_is_not_objective_success() -> None:
    truth = classify_browser_completion_truth(
        {
            "status": "completed",
            "material_browser_receipts": [
                {
                    "browser_receipt_readable": False,
                    "actual_backend_id": "",
                    "action_status": "",
                    "operation": "real_browser.search",
                }
            ],
            "public_evidence": [],
            "answer_claims": {"claims": [], "factual_supported_count": 0},
            "final_answer": {},
            "honest_blocker": {},
        }
    )

    assert truth["loop_closed"] is True
    assert truth["browser_body_reached"] is False
    assert truth["material_browser_action_succeeded"] is False
    assert truth["evidence_acquired"] is False
    assert truth["mission_objective_satisfied"] is False
    assert truth["useful_answer_completion"] is False


def test_structured_blind_evaluator_result_persists_safe_verdict_not_hash_only() -> None:
    result = normalize_blind_evaluator_result(
        {
            "evaluator_verdict": "QUALITY_GATE_FAIL",
            "answer_present": True,
            "evidence_present": True,
            "factual_claim_count": 2,
            "supported_claim_count": 1,
            "unsupported_claim_count": 1,
            "contradicted_claim_count": 0,
            "inference_preserved": True,
            "uncertainty_preserved": True,
            "objective_satisfaction_score": 0.5,
            "useful_answer_classification": "partial",
            "notes": "safe bounded note",
        },
        evaluator_called=True,
        evaluator_provider="aliyun_dashscope",
        evaluator_model="deepseek-v4-pro",
    )

    assert result["evaluator_called"] is True
    assert result["evaluator_verdict"] == "QUALITY_GATE_FAIL"
    assert result["factual_claim_count"] == 2
    assert result["supported_claim_count"] == 1
    assert result["unsupported_claim_count"] == 1
    assert result["response_hash"]
    assert "notes" not in result
    assert result["raw_output_persisted"] is False


def test_browser_proof_index_replay_hash_is_stable_and_no_react(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    result = host.run_product_action_kernel_task_loop(
        workspace_root=_workspace(tmp_path),
        session_id="browser-proof-index-replay",
        mission_objective="Search and finish with stable browser proof index replay.",
        decision_client=_browser_evidence_finish_client(),
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=6,
        max_material_actions=4,
    )

    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)
    payload = replay.safe_model_dump()

    assert payload["reexecuted_actions"] is False
    assert payload["receipt_writes_delta"] == 0
    assert payload["finalgate_writes_delta"] == 0
    assert payload["browser_proof_index_writes_delta"] == 0
    assert payload["browser_proof_index_hashes_stable"] is True
    assert payload["answer_claim_mutation_delta"] == 0


def test_browser_proof_index_context_summary_is_bounded(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    client = _browser_evidence_finish_client()
    result = host.run_product_action_kernel_task_loop(
        workspace_root=_workspace(tmp_path),
        session_id="browser-proof-index-context",
        mission_objective="Expose compact proof state to the model without repeating full receipts.",
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=6,
        max_material_actions=4,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    final_context = client.contexts[-1]
    summary = final_context["browser_proof_index_summary"]
    assert summary["material_browser_receipt_count"] >= 3
    assert summary["browser_receipt_missing_count"] == 0
    assert "receipt_payload" not in json.dumps(summary)
    assert len(json.dumps(summary)) < 3000


def _browser_evidence_finish_client() -> ProductActionKernelLoopDecisionClient:
    answer_claims = [
        {
            "claim_id": "claim:bounded-search",
            "claim_type": "sourced_factual_claim",
            "text": "The bounded browser page returned searchable evidence.",
            "evidence_refs": ["evidence:bounded-browser-search"],
            "confidence": 0.88,
        },
        {
            "claim_id": "claim:bounded-inference",
            "claim_type": "model_inference",
            "text": "The evidence is sufficient for this bounded local mission.",
            "confidence": 0.7,
        },
    ]
    return ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "pathlib glob", "engine_profile": "fake_product_search"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_evidence",
                params={"engine_profile": "fake_product_search"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.verify_extraction",
                params={"engine_profile": "fake_product_search"},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="summarize_evidence", params={}),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={
                    "safe_summary": "Bounded browser evidence mission completed.",
                    "final_answer": {
                        "answer_text": "The bounded browser page returned searchable evidence about Path.glob.",
                        "inference_policy": "Factual claims must reference public evidence.",
                    },
                    "answer_claims": answer_claims,
                    "public_evidence": [
                        {
                            "evidence_id": "evidence:bounded-browser-search",
                            "source_url": "https://bounded.example/docs/pathlib.html?highlight=glob&token=drop-me",
                            "source_title": "Bounded pathlib docs",
                            "source_origin": "https://bounded.example",
                            "excerpt": "Path.glob(pattern) returns matching paths for a relative pattern.",
                        }
                    ],
                },
            ),
        ]
    )


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir(exist_ok=True)
    (root / "README.md").write_text("# Browser proof index\n", encoding="utf-8")
    return root
