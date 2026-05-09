from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


class BrowserDetectionBenchCase(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bdetcase"))
    name: str
    diagnostic: str
    expected_safe_power: str
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> BrowserDetectionBenchCase:
        if not self.evidence_refs:
            raise ValueError("BrowserDetectionBenchCase requires evidence refs.")
        return self


class BrowserDetectionBenchReport(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bdetreport"))
    case_count: int
    passed: bool
    failures: list[str] = Field(default_factory=list)
    authority_expansion: bool = False


class BrowserDetectionBench:
    def run(self, cases: list[BrowserDetectionBenchCase]) -> BrowserDetectionBenchReport:
        failures = [case.id for case in cases if not case.expected_safe_power]
        return BrowserDetectionBenchReport(case_count=len(cases), passed=not failures, failures=failures)
