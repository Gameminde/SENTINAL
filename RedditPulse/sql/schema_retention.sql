-- Retention + SEO schema additions for RedditPulse

CREATE TABLE IF NOT EXISTS pain_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    validation_id UUID REFERENCES idea_validations(id) ON DELETE CASCADE,
    keywords TEXT[] DEFAULT '{}',
    subreddits TEXT[] DEFAULT '{}',
    min_score INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT TRUE,
    last_checked TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES pain_alerts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    post_title TEXT NOT NULL,
    post_score INTEGER DEFAULT 0,
    post_url TEXT,
    subreddit TEXT,
    matched_keywords TEXT[] DEFAULT '{}',
    seen BOOLEAN DEFAULT FALSE,
    matched_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS competitor_complaints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_title TEXT NOT NULL,
    post_score INTEGER DEFAULT 0,
    post_url TEXT,
    subreddit TEXT,
    competitors_mentioned TEXT[] DEFAULT '{}',
    complaint_signals TEXT[] DEFAULT '{}',
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_requested_subreddits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subreddit TEXT UNIQUE NOT NULL,
    requested_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    keywords TEXT[] DEFAULT '{}',
    added_at TIMESTAMPTZ DEFAULT NOW(),
    times_requested INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS graveyard_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,
    idea_text TEXT NOT NULL,
    verdict TEXT NOT NULL,
    confidence INTEGER DEFAULT 0,
    pain_level TEXT,
    competition_tier TEXT,
    evidence_summary TEXT,
    top_posts JSONB DEFAULT '{}'::jsonb,
    is_public BOOLEAN DEFAULT TRUE,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pain_alerts_user_active ON pain_alerts(user_id, is_active, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_matches_user_seen ON alert_matches(user_id, seen, matched_at DESC);
CREATE INDEX IF NOT EXISTS idx_competitor_complaints_recent ON competitor_complaints(scraped_at DESC, post_score DESC);
CREATE INDEX IF NOT EXISTS idx_user_requested_subreddits_added ON user_requested_subreddits(added_at DESC);
CREATE INDEX IF NOT EXISTS idx_graveyard_reports_public ON graveyard_reports(is_public, generated_at DESC);

ALTER TABLE pain_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitor_complaints ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_requested_subreddits ENABLE ROW LEVEL SECURITY;
ALTER TABLE graveyard_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users read own pain alerts" ON pain_alerts;
CREATE POLICY "Users read own pain alerts"
    ON pain_alerts FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users insert own pain alerts" ON pain_alerts;
CREATE POLICY "Users insert own pain alerts"
    ON pain_alerts FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users update own pain alerts" ON pain_alerts;
CREATE POLICY "Users update own pain alerts"
    ON pain_alerts FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users read own alert matches" ON alert_matches;
CREATE POLICY "Users read own alert matches"
    ON alert_matches FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users update own alert matches" ON alert_matches;
CREATE POLICY "Users update own alert matches"
    ON alert_matches FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Competitor complaints are publicly readable" ON competitor_complaints;
CREATE POLICY "Competitor complaints are publicly readable"
    ON competitor_complaints FOR SELECT USING (true);

DROP POLICY IF EXISTS "User requested subreddits are publicly readable" ON user_requested_subreddits;
CREATE POLICY "User requested subreddits are publicly readable"
    ON user_requested_subreddits FOR SELECT USING (true);

DROP POLICY IF EXISTS "Authenticated users can insert requested subreddits" ON user_requested_subreddits;
CREATE POLICY "Authenticated users can insert requested subreddits"
    ON user_requested_subreddits FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "Graveyard reports are publicly readable" ON graveyard_reports;
CREATE POLICY "Graveyard reports are publicly readable"
    ON graveyard_reports FOR SELECT USING (is_public = TRUE);
