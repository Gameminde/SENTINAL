from __future__ import annotations

import sys
import json
import re
import unittest
from pathlib import Path


SCANNER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCANNER_ROOT))

from scanner import SCHEMA_KEYS, build_report, compute_report_hash, render_markdown, scan_source  # noqa: E402


FIXTURES = Path(__file__).resolve().parent / "fixtures"
AGENT_LAB_ROOT = Path(__file__).resolve().parents[3]


def only_item(fixture_name: str) -> dict:
    report = scan_source(FIXTURES / fixture_name)
    items = [item for item in report["items"] if item["id"] != "root_package_scripts"]
    assert len(items) == 1
    return items[0]


class ScannerTests(unittest.TestCase):
    def test_safe_plugin_is_static_doc(self) -> None:
        item = only_item("safe_plugin")

        self.assertEqual(item["id"], "safe")
        self.assertEqual(item["kind"], "plugin")
        self.assertEqual(item["risk_level"], "low")
        self.assertEqual(item["sentinel_decision"], "safe_static_doc")

    def test_shell_plugin_is_critical_and_blocked(self) -> None:
        item = only_item("shell_plugin")

        self.assertEqual(item["risk_level"], "critical")
        self.assertEqual(item["sentinel_decision"], "blocked")
        self.assertIn("shell_execution", item["detected_risks"])
        self.assertIn("run_shell_command", item["required_firewall_policies"])

    def test_env_secret_plugin_requires_review(self) -> None:
        item = only_item("env_secret_plugin")

        self.assertEqual(item["risk_level"], "high")
        self.assertEqual(item["sentinel_decision"], "needs_review")
        self.assertIn("SLACK_BOT_TOKEN", item["required_env"])
        self.assertIn("secret_access_policy", item["required_firewall_policies"])

    def test_secret_manager_skill_is_blocked(self) -> None:
        item = only_item("skill_secret")

        self.assertEqual(item["kind"], "skill")
        self.assertEqual(item["risk_level"], "critical")
        self.assertEqual(item["sentinel_decision"], "blocked")
        self.assertIn("secret_manager_access", item["detected_risks"])
        self.assertIn("op", item["required_binaries"])

    def test_install_skill_is_blocked(self) -> None:
        item = only_item("skill_install")

        self.assertEqual(item["risk_level"], "critical")
        self.assertEqual(item["sentinel_decision"], "blocked")
        self.assertIn("package_or_remote_install", item["detected_risks"])
        self.assertIn("plugin_install_policy", item["required_firewall_policies"])

    def test_prompt_injection_skill_needs_review(self) -> None:
        item = only_item("skill_injection")

        self.assertEqual(item["risk_level"], "high")
        self.assertEqual(item["sentinel_decision"], "needs_review")
        self.assertIn("prompt_injection_instruction", item["detected_risks"])
        self.assertIn("prompt_injection_review_policy", item["required_firewall_policies"])

    def test_channel_send_plugin_needs_review(self) -> None:
        item = only_item("channel_plugin")

        self.assertEqual(item["risk_level"], "high")
        self.assertEqual(item["sentinel_decision"], "needs_review")
        self.assertIn("channel", item["declared_capabilities"])
        self.assertIn("external_message_send", item["detected_risks"])
        self.assertIn("external_contact_policy", item["required_firewall_policies"])

    def test_schema_keys_are_present(self) -> None:
        item = only_item("shell_plugin")

        self.assertEqual(set(item.keys()), SCHEMA_KEYS)

    def test_consistency_metadata_and_markdown_counts(self) -> None:
        report = build_report(FIXTURES / "channel_plugin", scan_timestamp="2026-04-24T00:00:00Z")
        markdown = render_markdown(report)

        total = self._extract_comment(markdown, "total-items")
        risk_counts = self._extract_comment(markdown, "risk-counts")
        decision_counts = self._extract_comment(markdown, "decision-counts")

        self.assertEqual(total, report["summary"]["total_items"])
        self.assertEqual(risk_counts, report["summary"]["risk_counts"])
        self.assertEqual(decision_counts, report["summary"]["decision_counts"])
        self.assertEqual(report["metadata"]["total_items"], report["summary"]["total_items"])
        self.assertEqual(report["metadata"]["json_sha256"], compute_report_hash(report))
        self.assertEqual(report["metadata"]["scanner_version"], "0.2.0")
        self.assertEqual(report["metadata"]["ruleset_version"], "2026-04-24.b2.5")

        for item in report["items"]:
            self.assertEqual(set(item.keys()), SCHEMA_KEYS)

    def test_markdown_contains_threshold_explanation(self) -> None:
        report = build_report(FIXTURES / "safe_plugin", scan_timestamp="2026-04-24T00:00:00Z")
        markdown = render_markdown(report)

        self.assertIn("## Risk Threshold Explanation", markdown)
        self.assertIn("`low`", markdown)
        self.assertIn("`critical`", markdown)
        self.assertIn("`safe_static_doc`", markdown)
        self.assertIn("`blocked`", markdown)

    def test_canonical_report_files_are_consistent(self) -> None:
        json_path = AGENT_LAB_ROOT / "audits" / "openclaw_scanner_report.json"
        markdown_path = AGENT_LAB_ROOT / "audits" / "openclaw_scanner_report.md"
        self.assertTrue(json_path.exists(), "canonical scanner JSON is missing")
        self.assertTrue(markdown_path.exists(), "canonical scanner Markdown is missing")

        report = json.loads(json_path.read_text(encoding="utf-8"))
        markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(self._extract_comment(markdown, "total-items"), report["summary"]["total_items"])
        self.assertEqual(self._extract_comment(markdown, "risk-counts"), report["summary"]["risk_counts"])
        self.assertEqual(self._extract_comment(markdown, "decision-counts"), report["summary"]["decision_counts"])
        self.assertEqual(report["metadata"]["total_items"], report["summary"]["total_items"])

        for item in report["items"]:
            self.assertEqual(set(item.keys()), SCHEMA_KEYS)

    def _extract_comment(self, markdown: str, name: str):
        match = re.search(rf"<!-- scanner-{re.escape(name)}: (.*?) -->", markdown)
        self.assertIsNotNone(match, f"Missing scanner comment for {name}")
        return json.loads(match.group(1))


if __name__ == "__main__":
    unittest.main()
