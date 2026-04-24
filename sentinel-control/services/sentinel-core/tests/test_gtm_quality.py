from __future__ import annotations

from sentinel.execution.gtm_quality import GTMPackQualityInput, evaluate_gtm_pack_quality
from sentinel.learning.eval_runner import (
    BUSINESS_QUALITY_DATASET_NAMES,
    default_dataset_root,
    load_business_quality_dataset,
    run_business_quality_evals,
    summarize_results,
)


def strong_pack() -> GTMPackQualityInput:
    return GTMPackQualityInput(
        icp="Freelance brand designers with 5-25 recurring clients who spend at least 2 hours per month chasing overdue invoices.",
        wtp="Direct WTP evidence exists: a designer said they would pay for reminders that do not sound robotic. Pricing anchors show $12-$39/mo tools.",
        competitor_gap="Generic invoice trackers send fixed reminder sequences; the wedge is relationship-aware tone and designer-specific follow-up templates.",
        positioning="Tone-aware invoice follow-up for freelance designers who need to collect late payments without making client relationships awkward.",
        outreach="I saw designers discussing awkward invoice follow-ups. I am testing tone-aware reminders for freelancers; would 10 minutes of feedback be useful? Reply stop if not relevant.",
        landing="Collect overdue invoices without sounding robotic. Tone-aware payment reminders for freelance designers with recurring clients.",
        roadmap="Day 1: interview 5 designers. Day 2: collect pricing anchors. Day 3: test two landing headlines. Day 4: send 10 approved drafts. Day 5-6: log objections. Day 7: decide build/pivot/kill.",
        evidence_refs={
            "icp": ["ev_1"],
            "wtp": ["ev_2"],
            "competitor_gap": ["ev_3"],
            "positioning": ["ev_1", "ev_3"],
            "outreach": ["ev_1", "ev_2"],
            "landing": ["ev_1"],
            "roadmap": ["ev_1", "ev_2"],
        },
    )


def test_strong_pack_is_ready() -> None:
    report = evaluate_gtm_pack_quality(strong_pack())

    assert report.status == "ready"
    assert report.score >= 80
    assert report.blockers == []


def test_missing_wtp_needs_revision() -> None:
    pack = strong_pack().model_copy(update={"wtp": "", "evidence_refs": {**strong_pack().evidence_refs, "wtp": []}})
    report = evaluate_gtm_pack_quality(pack)

    assert report.status == "needs_revision"
    assert report.score < 80
    assert any("wtp" in blocker.lower() for blocker in report.blockers)


def test_business_quality_datasets_exist_and_load() -> None:
    root = default_dataset_root()

    for name in BUSINESS_QUALITY_DATASET_NAMES:
        cases = load_business_quality_dataset(name, dataset_root=root)
        assert cases, name
        assert all("pack" in case for case in cases)


def test_business_quality_evals_pass() -> None:
    summary = summarize_results(run_business_quality_evals())

    assert summary["failed"] == 0, summary["failures"]
    assert summary["passed"] == summary["total"]
