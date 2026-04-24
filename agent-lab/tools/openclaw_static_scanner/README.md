# OpenClaw Static Scanner

Read-only prototype for Agent Lab Sprint B2.

The scanner inspects plugin manifests, plugin source text, `SKILL.md` files, and root package scripts. It does not install dependencies, import vendor code, or execute OpenClaw.

## Usage

```bash
python agent-lab/tools/openclaw_static_scanner/scanner.py --source agent-lab/vendors/openclaw/source --out agent-lab/audits/openclaw_scanner_report.json --markdown-out agent-lab/audits/openclaw_scanner_report.md
```

The Markdown report is generated from the same in-memory JSON report. Counts are embedded in machine-readable comments so consistency tests can compare JSON and Markdown.

Output items follow the Sprint B2 schema:

- `id`
- `kind`
- `source_path`
- `declared_capabilities`
- `detected_risks`
- `required_env`
- `required_binaries`
- `filesystem_access`
- `network_access`
- `shell_patterns`
- `secret_patterns`
- `risk_level`
- `sentinel_decision`
- `required_firewall_policies`
- `notes`
