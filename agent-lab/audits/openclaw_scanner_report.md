# OpenClaw Static Scanner Report

This report is generated from `openclaw_scanner_report.json` by `openclaw_static_scanner`.

<!-- scanner-total-items: 83 -->
<!-- scanner-risk-counts: {"critical": 52, "high": 29, "medium": 2} -->
<!-- scanner-decision-counts: {"blocked": 52, "draft_only_tool": 2, "needs_review": 29} -->

## Metadata

| Field | Value |
| --- | --- |
| scanner_version | 0.2.0 |
| ruleset_version | 2026-04-24.b2.5 |
| scan_timestamp | 2026-04-24T18:12:20Z |
| source_commit | a2288c2b09e621f89a915960398f58e200b3b69d |
| source_path | C:/Users/PC/Desktop/youcef/A/agent-lab/vendors/openclaw/source |
| total_items | 83 |
| json_sha256 | 3cc47f733eef993be50fb065adfd6298f848631c29232fc43199652cdb27dbcf |
| json_sha256_scope | sha256 of canonical JSON with metadata.json_sha256 set to an empty string |

## Summary

| Field | Value |
| --- | --- |
| total_items | 83 |
| total_plugins | 31 |
| total_skills | 52 |

## Risk Counts

| Risk Level | Count |
| --- | ---: |
| `critical` | 52 |
| `high` | 29 |
| `medium` | 2 |

## Sentinel Decision Counts

| Decision | Count |
| --- | ---: |
| `blocked` | 52 |
| `needs_review` | 29 |
| `draft_only_tool` | 2 |

## Risk Threshold Explanation

| Risk Level | Meaning |
| --- | --- |
| `low` | Static documentation or metadata with no detected side-effect surface. |
| `medium` | Local read/write, memory, channel shape, or binary requirement that may be safe only as a draft or reviewed tool. |
| `high` | External network/API, env secret references, browser control, external contact, HTTP routes, or prompt-injection-like instructions. |
| `critical` | Shell/exec/PTY, package or remote install, secret-manager access, background service, or install-time script surfaces. |

| Sentinel Decision | Meaning |
| --- | --- |
| `safe_static_doc` | May be used as static reference material only. |
| `draft_only_tool` | Concept can inspire dry-run/draft behavior, but cannot execute side effects. |
| `needs_review` | Requires human review, Firewall policy mapping, eval coverage, and approval design before any experimental adapter. |
| `blocked` | Cannot be installed, run, bridged, or promoted until a stronger sandbox and explicit policy gates exist. |

## Common Risk Patterns

| Risk Pattern | Count |
| --- | ---: |
| `network_api_access` | 66 |
| `external_binary_requirement` | 53 |
| `shell_execution` | 45 |
| `env_secret_or_config_reference` | 37 |
| `filesystem_access` | 26 |
| `external_message_send` | 22 |
| `channel_adapter` | 20 |
| `browser_control` | 16 |
| `http_route` | 13 |
| `memory_or_persistence` | 12 |
| `prompt_injection_instruction` | 12 |
| `package_or_remote_install` | 12 |
| `background_service` | 5 |
| `secret_manager_access` | 2 |
| `install_time_script` | 1 |

## Required Firewall Policies

| Policy | Count |
| --- | ---: |
| `network_access_policy` | 66 |
| `binary_allowlist_policy` | 53 |
| `run_shell_command` | 45 |
| `secret_access_policy` | 38 |
| `filesystem_access_policy` | 26 |
| `external_contact_policy` | 22 |
| `channel_adapter_policy` | 20 |
| `browser_sandbox_policy` | 16 |
| `plugin_install_policy` | 13 |
| `http_route_policy` | 13 |
| `memory_write_policy` | 12 |
| `prompt_injection_review_policy` | 12 |
| `background_service_policy` | 5 |

## Top High-Risk Items

| ID | Kind | Risk | Decision | Source | Detected risks |
| --- | --- | --- | --- | --- | --- |
| `zalouser` | `plugin` | `critical` | `blocked` | `extensions/zalouser/openclaw.plugin.json` | `channel_adapter`, `env_secret_or_config_reference`, `external_binary_requirement`, `external_message_send`, `filesystem_access`, `network_api_access`, `package_or_remote_install`, `shell_execution` |
| `zalo` | `plugin` | `critical` | `blocked` | `extensions/zalo/openclaw.plugin.json` | `channel_adapter`, `env_secret_or_config_reference`, `external_message_send`, `filesystem_access`, `http_route`, `network_api_access`, `shell_execution` |
| `weather` | `skill` | `critical` | `blocked` | `skills/weather/SKILL.md` | `external_binary_requirement`, `network_api_access`, `shell_execution` |
| `voice-call` | `plugin` | `critical` | `blocked` | `extensions/voice-call/openclaw.plugin.json` | `background_service`, `browser_control`, `channel_adapter`, `env_secret_or_config_reference`, `external_binary_requirement`, `filesystem_access`, `http_route`, `memory_or_persistence` |
| `voice-call` | `skill` | `critical` | `blocked` | `skills/voice-call/SKILL.md` | `shell_execution` |
| `video-frames` | `skill` | `critical` | `blocked` | `skills/video-frames/SKILL.md` | `external_binary_requirement`, `filesystem_access`, `network_api_access`, `shell_execution` |
| `twitch` | `plugin` | `critical` | `blocked` | `extensions/twitch/openclaw.plugin.json` | `browser_control`, `channel_adapter`, `env_secret_or_config_reference`, `external_message_send`, `filesystem_access`, `memory_or_persistence`, `network_api_access`, `prompt_injection_instruction` |
| `trello` | `skill` | `critical` | `blocked` | `skills/trello/SKILL.md` | `env_secret_or_config_reference`, `external_binary_requirement`, `network_api_access`, `shell_execution` |
| `tmux` | `skill` | `critical` | `blocked` | `skills/tmux/SKILL.md` | `external_binary_requirement`, `filesystem_access`, `network_api_access`, `package_or_remote_install`, `shell_execution` |
| `tlon` | `plugin` | `critical` | `blocked` | `extensions/tlon/openclaw.plugin.json` | `channel_adapter`, `filesystem_access`, `network_api_access`, `shell_execution` |
| `summarize` | `skill` | `critical` | `blocked` | `skills/summarize/SKILL.md` | `env_secret_or_config_reference`, `external_binary_requirement`, `network_api_access`, `shell_execution` |
| `skill-creator` | `skill` | `critical` | `blocked` | `skills/skill-creator/SKILL.md` | `browser_control`, `filesystem_access`, `prompt_injection_instruction`, `shell_execution` |
| `sherpa-onnx-tts` | `skill` | `critical` | `blocked` | `skills/sherpa-onnx-tts/SKILL.md` | `network_api_access`, `shell_execution` |
| `session-logs` | `skill` | `critical` | `blocked` | `skills/session-logs/SKILL.md` | `external_binary_requirement`, `memory_or_persistence`, `prompt_injection_instruction`, `shell_execution` |
| `sag` | `skill` | `critical` | `blocked` | `skills/sag/SKILL.md` | `env_secret_or_config_reference`, `external_binary_requirement`, `external_message_send`, `network_api_access`, `shell_execution` |
| `root_package_scripts` | `plugin` | `critical` | `blocked` | `package.json` | `external_binary_requirement`, `install_time_script`, `shell_execution` |
| `qwen-portal-auth` | `plugin` | `critical` | `blocked` | `extensions/qwen-portal-auth/openclaw.plugin.json` | `env_secret_or_config_reference`, `network_api_access`, `shell_execution` |
| `peekaboo` | `skill` | `critical` | `blocked` | `skills/peekaboo/SKILL.md` | `external_binary_requirement`, `network_api_access`, `shell_execution` |
| `openai-whisper-api` | `skill` | `critical` | `blocked` | `skills/openai-whisper-api/SKILL.md` | `env_secret_or_config_reference`, `external_binary_requirement`, `filesystem_access`, `network_api_access`, `shell_execution` |
| `openai-image-gen` | `skill` | `critical` | `blocked` | `skills/openai-image-gen/SKILL.md` | `browser_control`, `env_secret_or_config_reference`, `external_binary_requirement`, `filesystem_access`, `network_api_access`, `shell_execution` |
| `open-prose` | `plugin` | `critical` | `blocked` | `extensions/open-prose/openclaw.plugin.json` | `background_service`, `browser_control`, `external_binary_requirement`, `filesystem_access`, `http_route`, `memory_or_persistence`, `network_api_access`, `package_or_remote_install` |
| `obsidian` | `skill` | `critical` | `blocked` | `skills/obsidian/SKILL.md` | `external_binary_requirement`, `network_api_access`, `secret_manager_access` |
| `notion` | `skill` | `critical` | `blocked` | `skills/notion/SKILL.md` | `env_secret_or_config_reference`, `external_binary_requirement`, `filesystem_access`, `network_api_access`, `shell_execution` |
| `nostr` | `plugin` | `critical` | `blocked` | `extensions/nostr/openclaw.plugin.json` | `browser_control`, `channel_adapter`, `env_secret_or_config_reference`, `external_binary_requirement`, `external_message_send`, `filesystem_access`, `http_route`, `memory_or_persistence` |
| `nano-pdf` | `skill` | `critical` | `blocked` | `skills/nano-pdf/SKILL.md` | `external_binary_requirement`, `network_api_access`, `shell_execution` |

## Promotion Rule

No OpenClaw-inspired pattern moves toward Sentinel until it has scanner output, capability mapping, failure-mode entry, Firewall policy, dry-run preview, approval rule, trace schema, eval dataset, passing tests, and a rollback or disable switch.
