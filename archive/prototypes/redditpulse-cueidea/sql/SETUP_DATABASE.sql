-- ════════════════════════════════════════════════════════════
-- RedditPulse — ONE-SHOT SETUP
-- Copy this ENTIRE file and run it in Supabase SQL Editor
-- https://supabase.com/dashboard → SQL Editor → New Query → Paste → Run
-- ════════════════════════════════════════════════════════════

-- 1. SCANS TABLE
CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    keywords TEXT[] NOT NULL,
    duration TEXT NOT NULL DEFAULT '10min',
    status TEXT DEFAULT 'running',
    posts_found INTEGER DEFAULT 0,
    posts_analyzed INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scans_user ON scans(user_id);
CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status);

ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users see own scans" ON scans;
DROP POLICY IF EXISTS "Users select own scans" ON scans;
DROP POLICY IF EXISTS "Users insert own scans" ON scans;
DROP POLICY IF EXISTS "Users update own scans" ON scans;

CREATE POLICY "Users select own scans" ON scans
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own scans" ON scans
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users update own scans" ON scans
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- 2. AI ANALYSIS TABLE
CREATE TABLE IF NOT EXISTS ai_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    post_id TEXT,
    problem_description TEXT,
    urgency_score INTEGER DEFAULT 0,
    willingness_to_pay BOOLEAN DEFAULT false,
    wtp_evidence TEXT,
    opportunity_type TEXT DEFAULT 'unknown',
    market_size TEXT DEFAULT 'unknown',
    solution_idea TEXT,
    ai_model_used TEXT,
    raw_ai_response JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_scan ON ai_analysis(scan_id);
CREATE INDEX IF NOT EXISTS idx_ai_post ON ai_analysis(post_id);

ALTER TABLE ai_analysis ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users see own analysis" ON ai_analysis;
DROP POLICY IF EXISTS "Users insert own analysis" ON ai_analysis;

CREATE POLICY "Users see own analysis" ON ai_analysis
    FOR SELECT USING (scan_id IN (SELECT id FROM scans WHERE user_id = auth.uid()));
CREATE POLICY "Users insert own analysis" ON ai_analysis
    FOR INSERT WITH CHECK (scan_id IN (SELECT id FROM scans WHERE user_id = auth.uid()));

-- 3. LINK POSTS TO SCANS
ALTER TABLE posts ADD COLUMN IF NOT EXISTS scan_id UUID;

-- ════════════════════════════════════════════════════════════
-- DONE! You should see "Success. No rows returned" 
-- ════════════════════════════════════════════════════════════
