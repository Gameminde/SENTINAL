# AgentMemory Vendor Snapshot

Static research specimen for Sentinel Agent Lab.

## Source

- Repository: https://github.com/rohitg00/agentmemory
- Local source: `agent-lab/vendors/agentmemory/source`
- Clone mode: shallow source clone
- Local audited commit: `68fddd418e1bbcc41d32a1c61b7a78d91eb7c4dc`
- Date added to Agent Lab: 2026-05-19

## Lab Decision

AgentMemory is approved for source audit only.

Do not install dependencies, start the memory server, connect MCP clients, connect
real accounts, import real agent histories, call providers, or expose the REST/API
surface during this audit phase.

## Why It Is In The Lab

AgentMemory is directly relevant to Sentinel's LLM memory lab because it contains
practical mechanisms for:

- session and observation capture;
- durable memory records;
- working memory slots;
- lessons, routines, and preferences;
- BM25, vector, graph, and hybrid retrieval;
- temporal graph modeling;
- replay and timeline reconstruction;
- retention, auto-forget, and access tracking;
- privacy filtering and audit logging;
- integrations with Codex, OpenClaw, Hermes, and other agent runtimes.

Sentinel should harvest mechanisms only. Vendor code must not be bridged into
Sentinel runtime.

## Primary Audit Artifacts

- `agent-lab/audits/agentmemory_static_memory_audit.md`
- `agent-lab/sentinel_integration_notes/agentmemory_to_sentinel.md`
