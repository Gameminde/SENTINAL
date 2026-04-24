-- ═══════════════════════════════════════════════════════
-- Enrichment Cache — Deep signal storage (7-day TTL)
-- ═══════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS enrichment_cache (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    topic_slug      TEXT NOT NULL UNIQUE,
    topic_name      TEXT NOT NULL DEFAULT '',

    -- Stack Overflow signals
    so_questions    JSONB DEFAULT '[]'::jsonb,     -- top unanswered questions
    so_total        INT DEFAULT 0,                  -- total unanswered count
    so_top_tags     JSONB DEFAULT '[]'::jsonb,     -- most common tags

    -- GitHub signals
    gh_issues       JSONB DEFAULT '[]'::jsonb,     -- top issues by reactions
    gh_total        INT DEFAULT 0,                  -- total open issue count
    gh_top_repos    JSONB DEFAULT '[]'::jsonb,     -- repos with most issues

    -- G2 / Capterra signals (Phase 2)
    g2_gaps         JSONB DEFAULT '[]'::jsonb,
    g2_total        INT DEFAULT 0,

    -- App Store signals (Phase 2)
    appstore_pains  JSONB DEFAULT '[]'::jsonb,
    appstore_total  INT DEFAULT 0,

    -- Confirmed Gaps (triangulation: when 2+ sources agree)
    confirmed_gaps  JSONB DEFAULT '[]'::jsonb,

    -- Metadata
    enriched_at     TIMESTAMPTZ DEFAULT now(),
    expires_at      TIMESTAMPTZ DEFAULT (now() + INTERVAL '7 days'),
    status          TEXT DEFAULT 'pending',         -- pending | enriching | done | error
    error_message   TEXT,

    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Index for fast lookup + TTL checks
CREATE INDEX IF NOT EXISTS idx_enrichment_slug ON enrichment_cache(topic_slug);
CREATE INDEX IF NOT EXISTS idx_enrichment_expires ON enrichment_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_enrichment_status ON enrichment_cache(status);

-- RLS
ALTER TABLE enrichment_cache ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Enrichment cache is publicly readable" ON enrichment_cache;
CREATE POLICY "Enrichment cache is publicly readable" ON enrichment_cache
    FOR SELECT USING (true);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_enrichment_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_enrichment_updated ON enrichment_cache;
CREATE TRIGGER trg_enrichment_updated
    BEFORE UPDATE ON enrichment_cache
    FOR EACH ROW EXECUTE FUNCTION update_enrichment_timestamp();
