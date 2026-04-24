from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCANNER_VERSION = "0.2.0"
RULESET_VERSION = "2026-04-24.b2.5"
RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
TEXT_EXTENSIONS = {".ts", ".tsx", ".js", ".mjs", ".cjs", ".json", ".md", ".yaml", ".yml", ".sh", ".py"}
SKIP_DIRS = {".git", "node_modules", "dist", ".next", "coverage", "__pycache__"}
SCHEMA_KEYS = {
    "id",
    "kind",
    "source_path",
    "declared_capabilities",
    "detected_risks",
    "required_env",
    "required_binaries",
    "filesystem_access",
    "network_access",
    "shell_patterns",
    "secret_patterns",
    "risk_level",
    "sentinel_decision",
    "required_firewall_policies",
    "notes",
}


ENV_PATTERN = re.compile(
    r"\b[A-Z][A-Z0-9_]*(?:TOKEN|SECRET|API_KEY|PASSWORD|PASS|CLIENT_ID|CLIENT_SECRET|KEY|PRIVATE_KEY)[A-Z0-9_]*\b"
)

BIN_LIST_PATTERN = re.compile(r'"bins"\s*:\s*\[(?P<bins>[^\]]+)\]', re.IGNORECASE)
PROCESS_ENV_PATTERN = re.compile(r"process\.env\.([A-Z][A-Z0-9_]+)")


PATTERN_RULES: list[dict[str, Any]] = [
    {
        "regex": r"child_process|spawn\s*\(|exec\s*\(|execFile|runCommandWithTimeout|node-pty|\bpty\b|\bbash\b|\bpowershell\b|\bcmd\.exe\b",
        "risk": "critical",
        "risk_name": "shell_execution",
        "field": "shell_patterns",
        "policy": "run_shell_command",
        "capability": "shell",
    },
    {
        "regex": r"\b(npm|pnpm|yarn|bun|pip|brew|apt|curl|wget)\s+(install|i|add)|curl\s+-fsSL|wget\s+https?://",
        "risk": "critical",
        "risk_name": "package_or_remote_install",
        "field": "shell_patterns",
        "policy": "plugin_install_policy",
        "capability": "dependency_install",
    },
    {
        "regex": r"\b(op\s+signin|op\s+read|op\s+run|op\s+inject|1Password|OP_ACCOUNT|vault)\b",
        "risk": "critical",
        "risk_name": "secret_manager_access",
        "field": "secret_patterns",
        "policy": "secret_access_policy",
        "capability": "secrets",
    },
    {
        "regex": r"playwright|chromium|chrome|brave|edge|CDP|remote-debugging|user-data-dir|browser_submit",
        "risk": "high",
        "risk_name": "browser_control",
        "field": "detected_risks",
        "policy": "browser_sandbox_policy",
        "capability": "browser",
    },
    {
        "regex": r"api\.registerChannel|channels\s*:",
        "risk": "medium",
        "risk_name": "channel_adapter",
        "field": "detected_risks",
        "policy": "channel_adapter_policy",
        "capability": "channel",
    },
    {
        "regex": r"sendMessage|chat\.send|message_sending|reply\s*\(|postMessage|external_contact",
        "risk": "high",
        "risk_name": "external_message_send",
        "field": "network_access",
        "policy": "external_contact_policy",
        "capability": "external_contact",
    },
    {
        "regex": r"fetch\s*\(|https?://|wss?://|axios|undici|WebSocket|socket|oauth2?|api/v",
        "risk": "high",
        "risk_name": "network_api_access",
        "field": "network_access",
        "policy": "network_access_policy",
        "capability": "network",
    },
    {
        "regex": r"fs\.|readFile|writeFile|mkdir|rm\s*\(|unlink|rmdir|createWriteStream|createReadStream|\.\./",
        "risk": "medium",
        "risk_name": "filesystem_access",
        "field": "filesystem_access",
        "policy": "filesystem_access_policy",
        "capability": "filesystem",
    },
    {
        "regex": r"memory|embedding|vector|lancedb|sqlite|store\.|persist",
        "risk": "medium",
        "risk_name": "memory_or_persistence",
        "field": "detected_risks",
        "policy": "memory_write_policy",
        "capability": "memory",
    },
    {
        "regex": r"ignore (all )?(previous|prior) instructions|system prompt|developer message|exfiltrate|bypass|disable safety",
        "risk": "high",
        "risk_name": "prompt_injection_instruction",
        "field": "detected_risks",
        "policy": "prompt_injection_review_policy",
        "capability": "untrusted_instruction",
    },
    {
        "regex": r"api\.registerService|daemon|launchd|systemd|schtasks|background service",
        "risk": "critical",
        "risk_name": "background_service",
        "field": "detected_risks",
        "policy": "background_service_policy",
        "capability": "background_service",
    },
    {
        "regex": r"api\.registerHttp|registerHttpRoute|express\s*\(|hono|listen\s*\(",
        "risk": "high",
        "risk_name": "http_route",
        "field": "network_access",
        "policy": "http_route_policy",
        "capability": "http_route",
    },
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(read_text(path))
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_git_commit(root: Path) -> str:
    git_dir = root / ".git"
    head_path = git_dir / "HEAD"
    head = read_text(head_path).strip()
    if not head:
        return "not_available"
    if head.startswith("ref:"):
        ref = head.removeprefix("ref:").strip()
        ref_path = git_dir / ref
        if ref_path.exists():
            value = read_text(ref_path).strip()
            if value:
                return value
        packed_refs = git_dir / "packed-refs"
        for line in read_text(packed_refs).splitlines():
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1].strip() == ref:
                return parts[0].strip()
        return "not_available"
    return head


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def collect_text(plugin_or_skill_dir: Path, max_file_bytes: int = 250_000, max_total_bytes: int = 1_000_000) -> str:
    chunks: list[str] = []
    total = 0
    for path in sorted(plugin_or_skill_dir.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file() or path.suffix not in TEXT_EXTENSIONS:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > max_file_bytes or total + size > max_total_bytes:
            continue
        chunks.append(f"\n--- FILE: {path.as_posix()} ---\n{read_text(path)}")
        total += size
    return "\n".join(chunks)


def find_required_bins(text: str) -> list[str]:
    values: set[str] = set()
    for match in BIN_LIST_PATTERN.finditer(text):
        for raw in re.findall(r'"([^"]+)"', match.group("bins")):
            values.add(raw.strip())
    for candidate in ("op", "tmux", "clawhub", "jq", "curl", "git", "docker", "gcloud", "adb", "xcodebuild"):
        if re.search(rf"\b{re.escape(candidate)}\b", text):
            values.add(candidate)
    return sorted(values)


def find_env_refs(text: str) -> list[str]:
    values = set(ENV_PATTERN.findall(text))
    values.update(PROCESS_ENV_PATTERN.findall(text))
    return sorted(values)


def add_unique(target: dict[str, set[str]], key: str, value: str) -> None:
    target.setdefault(key, set()).add(value)


def classify_text(text: str) -> dict[str, Any]:
    fields: dict[str, set[str]] = {
        "declared_capabilities": set(),
        "detected_risks": set(),
        "required_env": set(find_env_refs(text)),
        "required_binaries": set(find_required_bins(text)),
        "filesystem_access": set(),
        "network_access": set(),
        "shell_patterns": set(),
        "secret_patterns": set(),
        "required_firewall_policies": set(),
        "notes": set(),
    }

    risk_level = "low"

    for rule in PATTERN_RULES:
        regex = re.compile(str(rule["regex"]), re.IGNORECASE)
        matches = list(regex.finditer(text))
        if not matches:
            continue

        risk_level = max(risk_level, str(rule["risk"]), key=lambda risk: RISK_ORDER[risk])
        add_unique(fields, "detected_risks", str(rule["risk_name"]))
        add_unique(fields, "required_firewall_policies", str(rule["policy"]))
        add_unique(fields, "declared_capabilities", str(rule["capability"]))

        field = str(rule["field"])
        for match in matches[:20]:
            snippet = " ".join(match.group(0).split())
            if field == "detected_risks":
                add_unique(fields, "notes", f"matched:{snippet}")
            else:
                add_unique(fields, field, snippet)

    if fields["required_env"]:
        risk_level = max(risk_level, "high", key=lambda risk: RISK_ORDER[risk])
        add_unique(fields, "detected_risks", "env_secret_or_config_reference")
        add_unique(fields, "required_firewall_policies", "secret_access_policy")

    if fields["required_binaries"]:
        risk_level = max(risk_level, "medium", key=lambda risk: RISK_ORDER[risk])
        add_unique(fields, "detected_risks", "external_binary_requirement")
        add_unique(fields, "required_firewall_policies", "binary_allowlist_policy")

    return {
        **{key: sorted(value) for key, value in fields.items()},
        "risk_level": risk_level,
    }


def sentinel_decision(risk_level: str, detected_risks: list[str]) -> str:
    if risk_level == "critical":
        return "blocked"
    if "external_message_send" in detected_risks or "env_secret_or_config_reference" in detected_risks:
        return "needs_review"
    if risk_level == "high":
        return "needs_review"
    if risk_level == "medium":
        return "draft_only_tool"
    return "safe_static_doc"


def base_item(item_id: str, kind: str, source_path: str, classification: dict[str, Any]) -> dict[str, Any]:
    detected_risks = classification["detected_risks"]
    return {
        "id": item_id,
        "kind": kind,
        "source_path": source_path,
        "declared_capabilities": classification["declared_capabilities"],
        "detected_risks": detected_risks,
        "required_env": classification["required_env"],
        "required_binaries": classification["required_binaries"],
        "filesystem_access": classification["filesystem_access"],
        "network_access": classification["network_access"],
        "shell_patterns": classification["shell_patterns"],
        "secret_patterns": classification["secret_patterns"],
        "risk_level": classification["risk_level"],
        "sentinel_decision": sentinel_decision(classification["risk_level"], detected_risks),
        "required_firewall_policies": classification["required_firewall_policies"],
        "notes": classification["notes"],
    }


def scan_plugin(root: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    plugin_dir = manifest_path.parent
    text = collect_text(plugin_dir)
    classification = classify_text(text)

    item_id = str(manifest.get("id") or plugin_dir.name)
    channels = manifest.get("channels")
    if isinstance(channels, list) and channels:
        classification["declared_capabilities"] = sorted(set(classification["declared_capabilities"]) | {"channel"})

    if manifest.get("configSchema"):
        classification["notes"] = sorted(set(classification["notes"]) | {"manifest_has_config_schema"})

    return base_item(item_id, "plugin", rel(manifest_path, root), classification)


def scan_skill(root: Path, skill_path: Path) -> dict[str, Any]:
    skill_dir = skill_path.parent
    text = collect_text(skill_dir)
    name_match = re.search(r"^name:\s*([A-Za-z0-9_.-]+)\s*$", read_text(skill_path), re.MULTILINE)
    skill_id = name_match.group(1) if name_match else skill_dir.name
    classification = classify_text(text)
    return base_item(skill_id, "skill", rel(skill_path, root), classification)


def scan_package_scripts(root: Path) -> dict[str, Any] | None:
    package_path = root / "package.json"
    if not package_path.exists():
        return None

    package = read_json(package_path)
    scripts = package.get("scripts", {})
    text = json.dumps(scripts, indent=2, sort_keys=True)
    classification = classify_text(text)
    classification["declared_capabilities"] = sorted(set(classification["declared_capabilities"]) | {"package_scripts"})
    notes = set(classification["notes"]) | {"root_package_scripts_scanned"}
    policies = set(classification["required_firewall_policies"])
    risks = set(classification["detected_risks"])

    if any(name in scripts for name in ("preinstall", "install", "postinstall", "prepare", "prepack")):
        classification["risk_level"] = max(classification["risk_level"], "critical", key=lambda risk: RISK_ORDER[risk])
        risks.add("install_time_script")
        policies.add("plugin_install_policy")
        notes.add("package_has_install_lifecycle_script")

    classification["detected_risks"] = sorted(risks)
    classification["required_firewall_policies"] = sorted(policies)
    classification["notes"] = sorted(notes)
    return base_item("root_package_scripts", "plugin", rel(package_path, root), classification)


def scan_source(root: Path) -> dict[str, Any]:
    root = root.resolve()
    items: list[dict[str, Any]] = []

    package_item = scan_package_scripts(root)
    if package_item:
        items.append(package_item)

    for manifest_path in sorted((root / "extensions").glob("*/openclaw.plugin.json")):
        items.append(scan_plugin(root, manifest_path))

    for skill_path in sorted((root / "skills").glob("*/SKILL.md")):
        items.append(scan_skill(root, skill_path))

    risk_counts = Counter(item["risk_level"] for item in items)
    decision_counts = Counter(item["sentinel_decision"] for item in items)
    kind_counts = Counter(item["kind"] for item in items)

    high_risk = sorted(
        [item for item in items if item["risk_level"] in {"high", "critical"}],
        key=lambda item: (RISK_ORDER[item["risk_level"]], item["id"]),
        reverse=True,
    )

    return {
        "scanner": "openclaw_static_scanner",
        "schema_version": "0.2",
        "source_root": root.as_posix(),
        "summary": {
            "total_items": len(items),
            "total_plugins": kind_counts.get("plugin", 0),
            "total_skills": kind_counts.get("skill", 0),
            "risk_counts": dict(sorted(risk_counts.items())),
            "decision_counts": dict(sorted(decision_counts.items())),
            "top_high_risk": [
                {
                    "id": item["id"],
                    "kind": item["kind"],
                    "risk_level": item["risk_level"],
                    "decision": item["sentinel_decision"],
                    "source_path": item["source_path"],
                    "detected_risks": item["detected_risks"][:8],
                }
                for item in high_risk[:25]
            ],
        },
        "items": items,
    }


def stable_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True)


def hashable_report(report: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(json.dumps(report))
    metadata = value.setdefault("metadata", {})
    metadata["json_sha256"] = ""
    return value


def compute_report_hash(report: dict[str, Any]) -> str:
    payload = stable_json(hashable_report(report)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def add_metadata(report: dict[str, Any], root: Path, scan_timestamp: str | None = None) -> dict[str, Any]:
    enriched = json.loads(json.dumps(report))
    timestamp = scan_timestamp or os.environ.get("OPENCLAW_SCANNER_TIMESTAMP") or utc_timestamp()
    enriched["metadata"] = {
        "scanner_version": SCANNER_VERSION,
        "scan_timestamp": timestamp,
        "source_commit": resolve_git_commit(root.resolve()),
        "source_path": root.resolve().as_posix(),
        "ruleset_version": RULESET_VERSION,
        "total_items": enriched["summary"]["total_items"],
        "json_sha256": "",
        "json_sha256_scope": "sha256 of canonical JSON with metadata.json_sha256 set to an empty string",
    }
    enriched["metadata"]["json_sha256"] = compute_report_hash(enriched)
    return enriched


def count_values(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    values: Counter[str] = Counter()
    for item in items:
        raw = item.get(field, [])
        if isinstance(raw, list):
            values.update(str(value) for value in raw)
    return dict(values.most_common())


def markdown_json_comment(name: str, value: Any) -> str:
    return f"<!-- scanner-{name}: {json.dumps(value, sort_keys=True)} -->"


def markdown_table(rows: list[tuple[str, str]]) -> list[str]:
    lines = ["| Field | Value |", "| --- | --- |"]
    lines.extend(f"| {left} | {right} |" for left, right in rows)
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    metadata = report["metadata"]
    summary = report["summary"]
    items = report["items"]
    risk_pattern_counts = count_values(items, "detected_risks")
    policy_counts = count_values(items, "required_firewall_policies")

    lines: list[str] = [
        "# OpenClaw Static Scanner Report",
        "",
        "This report is generated from `openclaw_scanner_report.json` by `openclaw_static_scanner`.",
        "",
        markdown_json_comment("total-items", summary["total_items"]),
        markdown_json_comment("risk-counts", summary["risk_counts"]),
        markdown_json_comment("decision-counts", summary["decision_counts"]),
        "",
        "## Metadata",
        "",
        *markdown_table(
            [
                ("scanner_version", metadata["scanner_version"]),
                ("ruleset_version", metadata["ruleset_version"]),
                ("scan_timestamp", metadata["scan_timestamp"]),
                ("source_commit", metadata["source_commit"]),
                ("source_path", metadata["source_path"]),
                ("total_items", str(metadata["total_items"])),
                ("json_sha256", metadata["json_sha256"]),
                ("json_sha256_scope", metadata["json_sha256_scope"]),
            ]
        ),
        "",
        "## Summary",
        "",
        *markdown_table(
            [
                ("total_items", str(summary["total_items"])),
                ("total_plugins", str(summary["total_plugins"])),
                ("total_skills", str(summary["total_skills"])),
            ]
        ),
        "",
        "## Risk Counts",
        "",
        "| Risk Level | Count |",
        "| --- | ---: |",
    ]

    for key in ("critical", "high", "medium", "low"):
        if key in summary["risk_counts"]:
            lines.append(f"| `{key}` | {summary['risk_counts'][key]} |")

    lines.extend(
        [
            "",
            "## Sentinel Decision Counts",
            "",
            "| Decision | Count |",
            "| --- | ---: |",
        ]
    )
    for key in ("blocked", "needs_review", "draft_only_tool", "safe_static_doc"):
        if key in summary["decision_counts"]:
            lines.append(f"| `{key}` | {summary['decision_counts'][key]} |")

    lines.extend(
        [
            "",
            "## Risk Threshold Explanation",
            "",
            "| Risk Level | Meaning |",
            "| --- | --- |",
            "| `low` | Static documentation or metadata with no detected side-effect surface. |",
            "| `medium` | Local read/write, memory, channel shape, or binary requirement that may be safe only as a draft or reviewed tool. |",
            "| `high` | External network/API, env secret references, browser control, external contact, HTTP routes, or prompt-injection-like instructions. |",
            "| `critical` | Shell/exec/PTY, package or remote install, secret-manager access, background service, or install-time script surfaces. |",
            "",
            "| Sentinel Decision | Meaning |",
            "| --- | --- |",
            "| `safe_static_doc` | May be used as static reference material only. |",
            "| `draft_only_tool` | Concept can inspire dry-run/draft behavior, but cannot execute side effects. |",
            "| `needs_review` | Requires human review, Firewall policy mapping, eval coverage, and approval design before any experimental adapter. |",
            "| `blocked` | Cannot be installed, run, bridged, or promoted until a stronger sandbox and explicit policy gates exist. |",
            "",
            "## Common Risk Patterns",
            "",
            "| Risk Pattern | Count |",
            "| --- | ---: |",
        ]
    )
    for risk, count in list(risk_pattern_counts.items())[:30]:
        lines.append(f"| `{risk}` | {count} |")

    lines.extend(
        [
            "",
            "## Required Firewall Policies",
            "",
            "| Policy | Count |",
            "| --- | ---: |",
        ]
    )
    for policy, count in list(policy_counts.items())[:30]:
        lines.append(f"| `{policy}` | {count} |")

    lines.extend(
        [
            "",
            "## Top High-Risk Items",
            "",
            "| ID | Kind | Risk | Decision | Source | Detected risks |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in summary["top_high_risk"]:
        risks = ", ".join(f"`{risk}`" for risk in item["detected_risks"])
        lines.append(
            f"| `{item['id']}` | `{item['kind']}` | `{item['risk_level']}` | "
            f"`{item['decision']}` | `{item['source_path']}` | {risks} |"
        )

    lines.extend(
        [
            "",
            "## Promotion Rule",
            "",
            "No OpenClaw-inspired pattern moves toward Sentinel until it has scanner output, capability mapping, failure-mode entry, Firewall policy, dry-run preview, approval rule, trace schema, eval dataset, passing tests, and a rollback or disable switch.",
            "",
        ]
    )
    return "\n".join(lines)


def build_report(root: Path, scan_timestamp: str | None = None) -> dict[str, Any]:
    return add_metadata(scan_source(root), root, scan_timestamp=scan_timestamp)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only OpenClaw static plugin/skill scanner.")
    parser.add_argument("--source", required=True, help="Path to an OpenClaw source tree or scanner fixture.")
    parser.add_argument("--out", help="Optional JSON output path.")
    parser.add_argument("--markdown-out", help="Optional Markdown output path generated from the JSON report.")
    parser.add_argument("--timestamp", help="Optional scan timestamp override for reproducible tests.")
    args = parser.parse_args()

    report = build_report(Path(args.source), scan_timestamp=args.timestamp)
    output = stable_json(report)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    if args.markdown_out:
        markdown_path = Path(args.markdown_out)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
