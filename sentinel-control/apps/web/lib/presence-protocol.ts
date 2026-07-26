export type PresenceState =
  | "DISCONNECTED"
  | "SLEEPING"
  | "LISTENING"
  | "UNDERSTANDING"
  | "PLANNING"
  | "OBSERVING"
  | "ACTING"
  | "VERIFYING"
  | "WAITING_AUTHORITY"
  | "RECOVERING"
  | "BLOCKED"
  | "COMPLETED"
  | "KILLED"
  | "TELEMETRY_INCOMPLETE";

export type TelemetryState = "COMPLETE" | "TELEMETRY_INCOMPLETE";

export type PresenceEventV1 = {
  schema_version: "presence_event_v1";
  event_id: string;
  mission_id: string;
  sequence: number;
  source_sequence: number;
  decision_index: number;
  timestamp: string;
  presence_state: PresenceState;
  event_kind:
    | "MISSION"
    | "DECISION"
    | "ACTION"
    | "OBSERVATION"
    | "PROOF"
    | "BLOCKER"
    | "GATE"
    | "TERMINAL"
    | "CLEANUP"
    | "TELEMETRY";
  safe_summary: string;
  provider_metadata: {
    provider_id?: string;
    model_id?: string;
    latency_ms?: number;
    input_tokens?: number;
    output_tokens?: number;
  };
  context_pack_hash: string;
  available_affordances: string[];
  normalized_decision: {
    capability_id?: string;
    operation?: string;
    params_hash?: string;
  };
  dispatch_status: string;
  product_receipt_ref: string;
  browser_receipt_ref: string;
  before_state_fingerprint: string;
  after_state_fingerprint: string;
  before_evidence_fingerprint: string;
  after_evidence_fingerprint: string;
  material_progress: boolean | null;
  authority_state: string;
  blocker: string;
  gate_results: Record<string, string>;
  first_causal_divergence_ref: string;
  telemetry_state: TelemetryState;
  ledger_head: string;
  event_hash: string;
  data_not_authority: true;
  can_grant_authority: false;
  can_execute: false;
};

export type PresenceReplayV1 = {
  schema_version: "presence_replay_archive_v1";
  mission_id: string;
  label: string;
  replay_mode: "artifact_history_reconstruction";
  events: PresenceEventV1[];
};

const base = {
  schema_version: "presence_event_v1" as const,
  mission_id: "mdn_css_has",
  provider_metadata: {
    provider_id: "persisted-provider",
    model_id: "persisted-model",
  },
  available_affordances: [] as string[],
  authority_state: "public_web_read_only",
  data_not_authority: true as const,
  can_grant_authority: false as const,
  can_execute: false as const,
};

export const presenceStreamConnectingEvent: PresenceEventV1 = {
  schema_version: "presence_event_v1",
  event_id: "presence_event_live_stream_connecting",
  mission_id: "presence_live_stream_pending",
  sequence: 0,
  source_sequence: 0,
  decision_index: 0,
  timestamp: "1970-01-01T00:00:00.000Z",
  presence_state: "DISCONNECTED",
  event_kind: "TELEMETRY",
  safe_summary: "Connecting to the live safe Presence stream.",
  provider_metadata: {},
  context_pack_hash: "",
  available_affordances: [],
  normalized_decision: {},
  dispatch_status: "",
  product_receipt_ref: "",
  browser_receipt_ref: "",
  before_state_fingerprint: "",
  after_state_fingerprint: "",
  before_evidence_fingerprint: "",
  after_evidence_fingerprint: "",
  material_progress: null,
  authority_state: "not_present_in_safe_projection",
  blocker: "",
  gate_results: {},
  first_causal_divergence_ref: "",
  telemetry_state: "TELEMETRY_INCOMPLETE",
  ledger_head: "",
  event_hash: "presence_hash_live_stream_connecting",
  data_not_authority: true,
  can_grant_authority: false,
  can_execute: false,
};

export const presenceStreamUnavailableEvent: PresenceEventV1 = {
  ...presenceStreamConnectingEvent,
  event_id: "presence_event_live_stream_unavailable",
  mission_id: "presence_live_stream_unavailable",
  safe_summary: "Live safe Presence stream is unavailable; no mission state is inferred.",
  event_hash: "presence_hash_live_stream_unavailable",
};

function event(
  sequence: number,
  value: Omit<
    PresenceEventV1,
    | "schema_version"
    | "event_id"
    | "mission_id"
    | "sequence"
    | "source_sequence"
    | "timestamp"
    | "provider_metadata"
    | "available_affordances"
    | "authority_state"
    | "event_hash"
    | "data_not_authority"
    | "can_grant_authority"
    | "can_execute"
  > &
    Partial<Pick<PresenceEventV1, "provider_metadata" | "available_affordances" | "authority_state">>,
): PresenceEventV1 {
  return {
    ...base,
    event_id: `presence_event_mdn_${sequence}`,
    sequence,
    source_sequence: sequence,
    timestamp: `2026-07-22T18:37:${String(sequence).padStart(2, "0")}+00:00`,
    event_hash: `presence_hash_mdn_${sequence}`,
    ...value,
  };
}

export const mdnPresenceReplay: PresenceReplayV1 = {
  schema_version: "presence_replay_archive_v1",
  mission_id: "mdn_css_has",
  label: "MDN - historical failure trace",
  replay_mode: "artifact_history_reconstruction",
  events: [
    event(0, {
      decision_index: 0,
      presence_state: "UNDERSTANDING",
      event_kind: "MISSION",
      safe_summary: "Mission accepted. Public MDN documentation only.",
      context_pack_hash: "",
      normalized_decision: {},
      dispatch_status: "persisted",
      product_receipt_ref: "",
      browser_receipt_ref: "",
      before_state_fingerprint: "",
      after_state_fingerprint: "",
      before_evidence_fingerprint: "",
      after_evidence_fingerprint: "",
      material_progress: null,
      blocker: "",
      gate_results: {},
      first_causal_divergence_ref: "",
      telemetry_state: "COMPLETE",
      ledger_head: "ledger_mdn_0",
    }),
    event(1, {
      decision_index: 1,
      presence_state: "PLANNING",
      event_kind: "DECISION",
      safe_summary: "Decision 1 selected a bounded browser search.",
      context_pack_hash: "ctx_mdn_1",
      normalized_decision: {
        capability_id: "real_browser_control",
        operation: "real_browser.search",
        params_hash: "params_search",
      },
      dispatch_status: "accepted",
      product_receipt_ref: "product_receipt_search",
      browser_receipt_ref: "browser_receipt_search",
      before_state_fingerprint: "state_0",
      after_state_fingerprint: "state_0",
      before_evidence_fingerprint: "evidence_0",
      after_evidence_fingerprint: "evidence_1",
      material_progress: true,
      blocker: "real_browser_search_control_not_found",
      gate_results: {},
      first_causal_divergence_ref: "",
      telemetry_state: "COMPLETE",
      ledger_head: "ledger_mdn_1",
    }),
    event(2, {
      decision_index: 2,
      presence_state: "OBSERVING",
      event_kind: "OBSERVATION",
      safe_summary: "The visible page was inspected for relevant evidence.",
      context_pack_hash: "ctx_mdn_2",
      normalized_decision: {
        capability_id: "real_browser_control",
        operation: "real_browser.extract_evidence",
        params_hash: "params_extract",
      },
      dispatch_status: "completed",
      product_receipt_ref: "product_receipt_extract",
      browser_receipt_ref: "browser_receipt_extract",
      before_state_fingerprint: "state_1",
      after_state_fingerprint: "state_1",
      before_evidence_fingerprint: "evidence_1",
      after_evidence_fingerprint: "evidence_2",
      material_progress: true,
      blocker: "",
      gate_results: {},
      first_causal_divergence_ref: "",
      telemetry_state: "COMPLETE",
      ledger_head: "ledger_mdn_2",
    }),
    event(3, {
      decision_index: 3,
      presence_state: "VERIFYING",
      event_kind: "PROOF",
      safe_summary: "Evidence verification completed with a readable browser receipt.",
      context_pack_hash: "ctx_mdn_3",
      normalized_decision: {
        capability_id: "real_browser_control",
        operation: "real_browser.verify_extraction",
        params_hash: "params_verify",
      },
      dispatch_status: "completed",
      product_receipt_ref: "product_receipt_verify",
      browser_receipt_ref: "browser_receipt_verify",
      before_state_fingerprint: "state_1",
      after_state_fingerprint: "state_1",
      before_evidence_fingerprint: "evidence_2",
      after_evidence_fingerprint: "evidence_2",
      material_progress: false,
      blocker: "",
      gate_results: { action_finalgate: "PASSED" },
      first_causal_divergence_ref: "",
      telemetry_state: "COMPLETE",
      ledger_head: "ledger_mdn_3",
    }),
    event(4, {
      decision_index: 4,
      presence_state: "PLANNING",
      event_kind: "DECISION",
      safe_summary: "Sentinel evaluated whether the evidence was sufficient.",
      context_pack_hash: "ctx_mdn_4",
      normalized_decision: {
        capability_id: "sentinel_loop",
        operation: "summarize_evidence",
        params_hash: "params_summary",
      },
      dispatch_status: "completed",
      product_receipt_ref: "product_receipt_summary",
      browser_receipt_ref: "",
      before_state_fingerprint: "state_1",
      after_state_fingerprint: "state_1",
      before_evidence_fingerprint: "evidence_2",
      after_evidence_fingerprint: "evidence_2",
      material_progress: false,
      blocker: "",
      gate_results: {},
      first_causal_divergence_ref: "",
      telemetry_state: "COMPLETE",
      ledger_head: "ledger_mdn_4",
    }),
    event(5, {
      decision_index: 5,
      presence_state: "TELEMETRY_INCOMPLETE",
      event_kind: "PROOF",
      safe_summary: "Browser observation failed without a readable browser receipt.",
      context_pack_hash: "ctx_mdn_5",
      normalized_decision: {
        capability_id: "real_browser_control",
        operation: "real_browser.observe",
        params_hash: "params_observe",
      },
      dispatch_status: "blocked",
      product_receipt_ref: "product_action_kernel_receipt_cf98fc984b54491aa05b08d3d81374a0",
      browser_receipt_ref: "",
      before_state_fingerprint: "state_1",
      after_state_fingerprint: "state_1",
      before_evidence_fingerprint: "evidence_2",
      after_evidence_fingerprint: "evidence_2",
      material_progress: false,
      blocker: "real_browser_runtime_dispatch_exception",
      gate_results: {},
      first_causal_divergence_ref:
        "divergence:5:BROWSER_OBSERVE_FAILURE_WITHOUT_PROGRESS",
      telemetry_state: "TELEMETRY_INCOMPLETE",
      ledger_head: "ledger_mdn_5",
    }),
    event(6, {
      decision_index: 6,
      presence_state: "RECOVERING",
      event_kind: "BLOCKER",
      safe_summary: "The repeated observation was suppressed because progress was not proven.",
      context_pack_hash: "ctx_mdn_6",
      normalized_decision: {
        capability_id: "real_browser_control",
        operation: "real_browser.observe",
        params_hash: "params_observe",
      },
      dispatch_status: "suppressed_repeated_action",
      product_receipt_ref: "",
      browser_receipt_ref: "",
      before_state_fingerprint: "state_1",
      after_state_fingerprint: "state_1",
      before_evidence_fingerprint: "evidence_2",
      after_evidence_fingerprint: "evidence_2",
      material_progress: false,
      blocker: "",
      gate_results: {},
      first_causal_divergence_ref: "",
      telemetry_state: "COMPLETE",
      ledger_head: "ledger_mdn_6",
    }),
    event(7, {
      decision_index: 7,
      presence_state: "TELEMETRY_INCOMPLETE",
      event_kind: "PROOF",
      safe_summary: "The recovery observation failed with the same historical proof gap.",
      context_pack_hash: "ctx_mdn_7",
      normalized_decision: {
        capability_id: "real_browser_control",
        operation: "real_browser.observe",
        params_hash: "params_observe_recovery",
      },
      dispatch_status: "blocked",
      product_receipt_ref: "product_action_kernel_receipt_8780634596bd4ba59490465ad054376b",
      browser_receipt_ref: "",
      before_state_fingerprint: "state_1",
      after_state_fingerprint: "state_1",
      before_evidence_fingerprint: "evidence_2",
      after_evidence_fingerprint: "evidence_2",
      material_progress: false,
      blocker: "real_browser_runtime_dispatch_exception",
      gate_results: {},
      first_causal_divergence_ref: "",
      telemetry_state: "TELEMETRY_INCOMPLETE",
      ledger_head: "ledger_mdn_7",
    }),
    event(8, {
      decision_index: 8,
      presence_state: "RECOVERING",
      event_kind: "BLOCKER",
      safe_summary: "A third no-progress repetition was stopped before dispatch.",
      context_pack_hash: "ctx_mdn_8",
      normalized_decision: {
        capability_id: "real_browser_control",
        operation: "real_browser.observe",
        params_hash: "params_observe",
      },
      dispatch_status: "suppressed_repeated_action",
      product_receipt_ref: "",
      browser_receipt_ref: "",
      before_state_fingerprint: "state_1",
      after_state_fingerprint: "state_1",
      before_evidence_fingerprint: "evidence_2",
      after_evidence_fingerprint: "evidence_2",
      material_progress: false,
      blocker: "BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS",
      gate_results: {},
      first_causal_divergence_ref: "",
      telemetry_state: "COMPLETE",
      ledger_head: "ledger_mdn_8",
    }),
    event(9, {
      decision_index: 8,
      presence_state: "VERIFYING",
      event_kind: "PROOF",
      safe_summary: "Proof index persisted with two missing browser receipts.",
      context_pack_hash: "ctx_mdn_8",
      normalized_decision: {},
      dispatch_status: "persisted",
      product_receipt_ref: "",
      browser_receipt_ref: "",
      before_state_fingerprint: "state_1",
      after_state_fingerprint: "state_1",
      before_evidence_fingerprint: "evidence_2",
      after_evidence_fingerprint: "evidence_2",
      material_progress: false,
      blocker: "",
      gate_results: { material_browser_receipts: "FAILED" },
      first_causal_divergence_ref: "",
      telemetry_state: "TELEMETRY_INCOMPLETE",
      ledger_head: "ledger_mdn_9",
    }),
    event(10, {
      decision_index: 8,
      presence_state: "BLOCKED",
      event_kind: "GATE",
      safe_summary: "FinalGate rejected completion.",
      context_pack_hash: "",
      normalized_decision: {},
      dispatch_status: "blocked",
      product_receipt_ref: "",
      browser_receipt_ref: "",
      before_state_fingerprint: "",
      after_state_fingerprint: "",
      before_evidence_fingerprint: "",
      after_evidence_fingerprint: "",
      material_progress: false,
      blocker: "BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS",
      gate_results: { finalgate: "FAILED" },
      first_causal_divergence_ref: "",
      telemetry_state: "COMPLETE",
      ledger_head: "ledger_mdn_10",
    }),
    event(11, {
      decision_index: 8,
      presence_state: "BLOCKED",
      event_kind: "TERMINAL",
      safe_summary: "Mission blocked honestly. No useful answer was certified.",
      context_pack_hash: "",
      normalized_decision: {},
      dispatch_status: "blocked",
      product_receipt_ref: "",
      browser_receipt_ref: "",
      before_state_fingerprint: "",
      after_state_fingerprint: "",
      before_evidence_fingerprint: "",
      after_evidence_fingerprint: "",
      material_progress: false,
      blocker: "BROWSER_REPEATED_ACTION_WITHOUT_PROGRESS",
      gate_results: { finalgate: "FAILED" },
      first_causal_divergence_ref: "",
      telemetry_state: "COMPLETE",
      ledger_head: "ledger_mdn_11",
    }),
  ],
};
