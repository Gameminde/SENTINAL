from __future__ import annotations

import pytest

from sentinel.agent import (
    AuthorityCardBuilder,
    ContextBudgetPolicy,
    ContextCompressionResult,
    ContextNeedEstimator,
    DecisionFrameVerifier,
    EvidenceRanker,
    LLMDecisionFrame,
    ModelCapabilityProfile,
    ModelCostProfile,
    PromptBudgetAllocator,
    QualityExpectationContract,
    ReceiptGraphRetriever,
    ReceiptRecord,
    StateCardBuilder,
    ToolSurfaceRouter,
    UserModelContract,
)


def selected_model(max_frame_tokens: int = 2_000) -> UserModelContract:
    model = "deepseek-v4-pro"
    return UserModelContract(
        selected_model=model,
        cost_profile=ModelCostProfile(
            model_name=model,
            input_usd_per_1m=0.14,
            output_usd_per_1m=0.28,
            cached_input_usd_per_1m=0.07,
            context_window_tokens=128_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=model,
            context_window_tokens=128_000,
            supports_tool_calling=True,
            supports_prompt_caching=True,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=max_frame_tokens,
            max_tool_schema_tokens=320,
            max_evidence_tokens=1_000,
            reserve_output_tokens=500,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="broad_exploration",
            minimum_evidence_refs=3,
            retry_budget=1,
        ),
    )


def receipts() -> list[ReceiptRecord]:
    return [
        ReceiptRecord(
            receipt_id="r_browser",
            source_type="browser",
            summary="Public browser page shows pricing and source evidence.",
            text="browser public page evidence " * 600,
            evidence_refs=["ev_browser"],
            relevance_tags=["pricing", "evidence", "browser"],
            critical=True,
        ),
        ReceiptRecord(
            receipt_id="r_api",
            source_type="api",
            summary="API response validates market signal.",
            text="api response market signal " * 400,
            evidence_refs=["ev_api"],
            relevance_tags=["market", "api"],
        ),
        ReceiptRecord(
            receipt_id="r_channel",
            source_type="channel",
            summary="Draft response prepared but not sent.",
            text="channel draft " * 350,
            evidence_refs=["ev_channel"],
            relevance_tags=["draft"],
        ),
        ReceiptRecord(
            receipt_id="r_noise",
            source_type="workspace",
            summary="Unrelated old workspace notes.",
            text="noise " * 3_000,
            evidence_refs=["ev_noise"],
            relevance_tags=["old"],
        ),
    ]


def build_frame(max_frame_tokens: int = 2_000) -> LLMDecisionFrame:
    engine = ContextNeedEstimator()
    need = engine.estimate(
        mission_id="mission_p6r",
        objective="Compare pricing evidence and choose the next authorized browser or api step.",
        blockers=["Need current source evidence", "No live send authority"],
        required_evidence_refs=["ev_browser", "ev_api"],
        candidate_tools=["browser_read", "api_get", "channel_send", "desktop_write", "shell_exec"],
    )
    ranked = ReceiptGraphRetriever().retrieve_top_k(
        receipts(),
        need=need,
        k=3,
    )
    tools = ToolSurfaceRouter().select_tools(
        candidate_tools=need.candidate_tools,
        need=need,
        allowed_tools=["browser_read", "api_get", "desktop_write"],
        forbidden_tools=["channel_send", "shell_exec"],
    )
    allocator = PromptBudgetAllocator(selected_model(max_frame_tokens))
    return LLMDecisionFrame.build(
        mission_id=need.mission_id,
        mission_card=StateCardBuilder().mission_card(need),
        authority_card=AuthorityCardBuilder().authority_card(
            allowed_tools=["browser_read", "api_get", "desktop_write"],
            forbidden_tools=["channel_send", "shell_exec"],
            constraints=["no live send", "no shell execution"],
        ),
        progress_card=StateCardBuilder().progress_card(
            completed=["browser read complete"],
            pending=["api confirmation"],
        ),
        evidence=EvidenceRanker().rank(ranked, need),
        selected_tool_surface=tools,
        current_blockers=need.blockers,
        next_decision_options=["read another public page", "call read-only API"],
        required_output_schema={"decision": "string", "receipt_refs": "list[str]"},
        budget_allocator=allocator,
    )


def test_decision_frame_preserves_authority_constraints():
    frame = build_frame()

    assert "no live send" in frame.authority_card["constraints"]
    assert "channel_send" in frame.authority_card["forbidden_tools"]
    assert frame.authority_expansion is False


def test_authority_card_removes_forbidden_allowed_overlap():
    card = AuthorityCardBuilder().authority_card(
        allowed_tools=["api_get", "shell_exec"],
        forbidden_tools=["shell_exec"],
        constraints=["no shell"],
    )

    assert card["allowed_tools"] == ["api_get"]
    assert card["forbidden_tools"] == ["shell_exec"]


def test_decision_frame_preserves_critical_evidence_refs():
    frame = build_frame()

    assert "ev_browser" in frame.all_evidence_refs()
    assert "ev_api" in frame.all_evidence_refs()
    assert "r_browser" in frame.receipt_refs
    assert "r_noise" not in frame.receipt_refs


def test_receipt_graph_retriever_selects_top_k_relevant_receipts():
    need = ContextNeedEstimator().estimate(
        mission_id="mission",
        objective="Need browser pricing and api market evidence.",
        required_evidence_refs=["ev_browser"],
    )

    selected = ReceiptGraphRetriever().retrieve_top_k(receipts(), need=need, k=2)

    assert [receipt.receipt_id for receipt in selected] == ["r_browser", "r_api"]


def test_tool_surface_router_exposes_only_relevant_tools():
    need = ContextNeedEstimator().estimate(
        mission_id="mission",
        objective="Need browser and api evidence.",
        candidate_tools=["browser_read", "api_get", "channel_send", "shell_exec"],
    )

    tools = ToolSurfaceRouter().select_tools(
        candidate_tools=need.candidate_tools,
        need=need,
        allowed_tools=["browser_read", "api_get"],
        forbidden_tools=["channel_send", "shell_exec"],
    )

    assert tools == ["api_get", "browser_read"]


def test_prompt_budget_allocator_respects_user_model_contract():
    frame = build_frame(max_frame_tokens=1_000)

    assert frame.token_count <= 1_000
    assert frame.prompt_budget_respected is True
    assert frame.user_selected_model == "deepseek-v4-pro"


def test_prompt_budget_allocator_flags_over_budget_frame():
    allocator = PromptBudgetAllocator(selected_model(max_frame_tokens=1_000))

    token_count = allocator.estimate_frame_tokens("x" * 20_000)

    assert token_count > 1_000
    assert allocator.within_budget(token_count) is False


def test_decision_frame_keeps_exact_receipts_outside_prompt():
    frame = build_frame()
    rendered = frame.render_prompt_text()

    assert "receipt_refs" in rendered
    assert "browser public page evidence " * 10 not in rendered
    assert frame.raw_receipts_included is False


def test_raw_30k_context_compresses_to_1k_2k_frame():
    raw_context = "very long mission context " * 5_000
    result = ContextCompressionResult.from_frame(raw_context=raw_context, frame=build_frame())

    assert 20_000 <= result.raw_context_tokens <= 35_000
    assert 1_000 <= result.decision_frame_tokens <= 2_000
    assert result.compression_ratio < 0.10


def test_context_compression_result_checks_required_evidence_refs():
    frame = build_frame()
    passing = ContextCompressionResult.from_frame(
        raw_context="mission context " * 100,
        frame=frame,
        required_evidence_refs=["ev_browser"],
    )
    failing = ContextCompressionResult.from_frame(
        raw_context="mission context " * 100,
        frame=frame,
        required_evidence_refs=["ev_missing"],
    )

    assert passing.critical_evidence_preserved is True
    assert failing.critical_evidence_preserved is False


def test_frame_hash_is_deterministic():
    one = build_frame()
    two = build_frame()

    assert one.frame_hash == two.frame_hash
    assert one.deterministic_frame_hash is True


def test_secret_like_content_is_not_in_frame():
    secret_receipts = [
        ReceiptRecord(
            receipt_id="r_secret",
            source_type="workspace",
            summary="Contains API key",
            text="OPENAI_API_KEY=sk-secret-value " * 80,
            evidence_refs=["ev_secret"],
            relevance_tags=["pricing"],
            critical=True,
        )
    ]
    need = ContextNeedEstimator().estimate(
        mission_id="mission_secret",
        objective="Need pricing evidence.",
        required_evidence_refs=["ev_secret"],
    )
    ranked = ReceiptGraphRetriever().retrieve_top_k(secret_receipts, need=need, k=1)

    frame = LLMDecisionFrame.build(
        mission_id="mission_secret",
        mission_card=StateCardBuilder().mission_card(need),
        authority_card=AuthorityCardBuilder().authority_card(allowed_tools=[], forbidden_tools=[], constraints=[]),
        progress_card=StateCardBuilder().progress_card(completed=[], pending=[]),
        evidence=EvidenceRanker().rank(ranked, need),
        selected_tool_surface=[],
        current_blockers=[],
        next_decision_options=["review sanitized evidence"],
        required_output_schema={"decision": "string"},
        budget_allocator=PromptBudgetAllocator(selected_model()),
    )

    assert "sk-secret-value" not in frame.render_prompt_text()
    assert frame.raw_secret_leakage is False


def test_secret_like_content_is_not_stored_inside_frame_cards():
    need = ContextNeedEstimator().estimate(
        mission_id="mission_secret_card",
        objective="Review sk-secret-value without leaking it.",
        blockers=["token=abc123 must stay out of frame state"],
    )

    frame = LLMDecisionFrame.build(
        mission_id="mission_secret_card",
        mission_card=StateCardBuilder().mission_card(need),
        authority_card=AuthorityCardBuilder().authority_card(allowed_tools=[], forbidden_tools=[], constraints=[]),
        progress_card=StateCardBuilder().progress_card(completed=["password=hunter2"], pending=[]),
        evidence=[],
        selected_tool_surface=[],
        current_blockers=need.blockers,
        next_decision_options=["inspect sk-secret-value"],
        required_output_schema={"token": "do not leak token=abc123"},
        budget_allocator=PromptBudgetAllocator(selected_model()),
    )
    stored = str(frame.model_dump())

    assert "sk-secret-value" not in stored
    assert "abc123" not in stored
    assert "hunter2" not in stored
    assert frame.raw_secret_leakage is False


def test_secret_like_content_in_payload_keys_is_redacted():
    need = ContextNeedEstimator().estimate(
        mission_id="mission_secret_key",
        objective="Review payload keys.",
    )

    frame = LLMDecisionFrame.build(
        mission_id="mission_secret_key",
        mission_card=StateCardBuilder().mission_card(need) | {"sk-secret-value": "key label"},
        authority_card=AuthorityCardBuilder().authority_card(allowed_tools=[], forbidden_tools=[], constraints=[]),
        progress_card=StateCardBuilder().progress_card(completed=[], pending=[]),
        evidence=[],
        selected_tool_surface=[],
        current_blockers=[],
        next_decision_options=[],
        required_output_schema={"password=hunter2": "string"},
        budget_allocator=PromptBudgetAllocator(selected_model()),
    )
    stored = str(frame.model_dump())

    assert "sk-secret-value" not in stored
    assert "hunter2" not in stored


def test_missing_critical_evidence_fails_verifier():
    frame = build_frame()
    broken = frame.model_copy(update={"top_k_evidence": []})

    # Task 8 / CP-8.1: known_receipt_ids is now mandatory. This test
    # isolates the required-evidence-ref failure path, so we pass an
    # empty known_receipt_ids to keep the frame's receipt refs from
    # generating unrelated unresolvable failures. The empty set is a
    # zero-trust graph; the frame under test has an emptied
    # top_k_evidence, so the frame.receipt_refs that would normally
    # fail are irrelevant to this assertion's failure string.
    result = DecisionFrameVerifier(
        required_evidence_refs=["ev_browser"],
        known_receipt_ids=set(frame.receipt_refs),
    ).verify(broken)

    assert result.passed is False
    assert "missing critical evidence ref: ev_browser" in result.failures


def test_verifier_checks_receipt_refs_against_known_graph():
    frame = build_frame()

    # Task 8 / CP-8.1: required_evidence_refs is now mandatory. This
    # test isolates the receipt-resolvability failure path, so we pass
    # an explicit empty list; the frame's evidence refs are fine for
    # the purposes of this assertion.
    result = DecisionFrameVerifier(
        required_evidence_refs=[],
        known_receipt_ids=["r_browser"],
    ).verify(frame)

    assert result.passed is False
    assert "unresolvable receipt ref: r_api" in result.failures


def test_verifier_treats_empty_known_receipt_graph_as_authoritative():
    frame = build_frame()

    # Task 8 / CP-8.1: required_evidence_refs is now mandatory. An
    # explicit empty known_receipt_ids encodes zero-trust — every
    # receipt ref in the frame SHALL be reported unresolvable.
    result = DecisionFrameVerifier(
        required_evidence_refs=[],
        known_receipt_ids=[],
    ).verify(frame)

    assert result.passed is False
    assert "unresolvable receipt ref: r_api" in result.failures
    assert "unresolvable receipt ref: r_browser" in result.failures
