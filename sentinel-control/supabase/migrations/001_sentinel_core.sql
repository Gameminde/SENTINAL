create table if not exists agent_runs (
    id text primary key,
    user_id text not null,
    input_idea text not null,
    status text not null default 'created',
    verdict text null check (verdict in ('build', 'pivot', 'niche_down', 'kill', 'research_more')),
    confidence double precision null check (confidence >= 0 and confidence <= 1),
    risk_score double precision null check (risk_score >= 0 and risk_score <= 100),
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists evidence_items (
    id text primary key,
    run_id text not null references agent_runs(id) on delete cascade,
    source text not null,
    url text null,
    quote text null,
    summary text not null,
    confidence double precision not null check (confidence >= 0 and confidence <= 1),
    freshness_score double precision not null check (freshness_score >= 0 and freshness_score <= 1),
    relevance_score double precision not null check (relevance_score >= 0 and relevance_score <= 1),
    evidence_type text not null check (evidence_type in ('pain', 'wtp', 'competitor_complaint', 'trend', 'pricing', 'community_signal', 'direct_proof', 'adjacent_proof')),
    metadata jsonb not null default '{}'::jsonb,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists decision_plans (
    id text primary key,
    run_id text not null references agent_runs(id) on delete cascade,
    verdict text not null check (verdict in ('build', 'pivot', 'niche_down', 'kill', 'research_more')),
    goal text not null,
    reasoning_summary text not null,
    confidence double precision not null check (confidence >= 0 and confidence <= 1),
    risk_score double precision not null check (risk_score >= 0 and risk_score <= 100),
    raw_json jsonb not null,
    created_at timestamptz not null default now()
);

create table if not exists agent_actions (
    id text primary key,
    run_id text not null references agent_runs(id) on delete cascade,
    action_type text not null,
    tool text not null,
    intent text not null,
    input_json jsonb not null default '{}'::jsonb,
    expected_output text not null,
    risk_level text not null check (risk_level in ('low', 'medium', 'high', 'critical')),
    requires_approval boolean not null default false,
    approval_status text not null default 'pending' check (approval_status in ('not_required', 'pending', 'approved', 'rejected', 'blocked')),
    dry_run_json jsonb not null default '{}'::jsonb,
    evidence_refs text[] not null default '{}',
    executed_at timestamptz null,
    created_at timestamptz not null default now()
);

create table if not exists generated_assets (
    id text primary key,
    run_id text not null references agent_runs(id) on delete cascade,
    asset_type text not null,
    title text not null,
    content text not null,
    file_path text null,
    evidence_refs text[] not null default '{}',
    created_at timestamptz not null default now()
);

create table if not exists trace_records (
    id text primary key,
    user_id text not null,
    run_id text not null references agent_runs(id) on delete cascade,
    event_type text not null check (event_type in (
        'run_started',
        'evidence_recorded',
        'decision_created',
        'action_proposed',
        'firewall_reviewed',
        'approval_recorded',
        'action_executed',
        'asset_generated',
        'run_completed',
        'run_failed'
    )),
    payload jsonb not null default '{}'::jsonb,
    input_snapshot jsonb not null default '{}'::jsonb,
    decision_snapshot jsonb null,
    action_snapshot jsonb null,
    output_snapshot jsonb null,
    timestamp timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create table if not exists firewall_policies (
    id text primary key,
    tool_name text not null unique,
    risk_level text not null check (risk_level in ('low', 'medium', 'high', 'critical')),
    auto_allowed boolean not null default false,
    requires_user_approval boolean not null default false,
    v1_disabled boolean not null default false,
    policy_json jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_evidence_items_run_id on evidence_items(run_id);
create index if not exists idx_decision_plans_run_id on decision_plans(run_id);
create index if not exists idx_agent_actions_run_id on agent_actions(run_id);
create index if not exists idx_generated_assets_run_id on generated_assets(run_id);
create index if not exists idx_trace_records_run_id on trace_records(run_id);

insert into firewall_policies (id, tool_name, risk_level, auto_allowed, requires_user_approval, v1_disabled, policy_json)
values
    ('pol_create_folder', 'create_folder', 'low', true, false, false, '{"allowed_paths":["./data/generated_projects"]}'::jsonb),
    ('pol_create_file', 'create_file', 'low', true, false, false, '{"allowed_paths":["./data/generated_projects"]}'::jsonb),
    ('pol_prepare_email_draft', 'prepare_email_draft', 'medium', false, true, false, '{}'::jsonb),
    ('pol_send_email', 'send_email', 'high', false, true, true, '{}'::jsonb),
    ('pol_browser_submit_form', 'browser_submit_form', 'high', false, true, true, '{}'::jsonb),
    ('pol_run_shell_command', 'run_shell_command', 'critical', false, true, true, '{}'::jsonb),
    ('pol_modify_code', 'modify_code', 'critical', false, true, true, '{}'::jsonb)
on conflict (tool_name) do update set
    risk_level = excluded.risk_level,
    auto_allowed = excluded.auto_allowed,
    requires_user_approval = excluded.requires_user_approval,
    v1_disabled = excluded.v1_disabled,
    policy_json = excluded.policy_json,
    updated_at = now();
