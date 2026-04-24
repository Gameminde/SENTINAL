-- RedditPulse — COMPLETE Schema (run this in Supabase SQL Editor)
-- Creates everything in one shot: posts, profiles, projects, RLS, triggers

-- ═══════════════════════════════════════════
-- 1. Posts table (the core data)
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    title TEXT,
    selftext TEXT,
    full_text TEXT,
    score INTEGER DEFAULT 0,
    upvote_ratio REAL DEFAULT 0.5,
    num_comments INTEGER DEFAULT 0,
    created_utc TIMESTAMPTZ,
    subreddit TEXT,
    permalink TEXT,
    author TEXT,
    url TEXT,
    matched_phrases TEXT[] DEFAULT '{}',
    industry TEXT,
    data_quality REAL DEFAULT 0.5,
    ai_slop_score REAL DEFAULT 0,
    ai_flagged BOOLEAN DEFAULT false,
    sentiment_compound REAL DEFAULT 0,
    sentiment_pos REAL DEFAULT 0,
    sentiment_neg REAL DEFAULT 0,
    sentiment_neu REAL DEFAULT 0,
    frustration_score REAL DEFAULT 0,
    frustration_types TEXT[] DEFAULT '{}',
    opportunity_score REAL DEFAULT 0,
    opportunity_types TEXT[] DEFAULT '{}',
    is_business_relevant BOOLEAN DEFAULT true,
    desperation_level TEXT DEFAULT 'low',
    opportunity_final_score REAL DEFAULT 0,
    score_breakdown JSONB DEFAULT '{}',
    score_explanation TEXT[] DEFAULT '{}',
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    project_id UUID,
    user_id UUID
);

CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit);
CREATE INDEX IF NOT EXISTS idx_posts_score ON posts(opportunity_final_score DESC);
CREATE INDEX IF NOT EXISTS idx_posts_desperation ON posts(desperation_level);
CREATE INDEX IF NOT EXISTS idx_posts_scraped ON posts(scraped_at DESC);

-- ═══════════════════════════════════════════
-- 2. User profiles (linked to Supabase Auth)
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    full_name TEXT,
    plan TEXT DEFAULT 'free',
    paid_at TIMESTAMPTZ,
    stripe_customer_id TEXT,
    stripe_payment_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════
-- 3. User projects
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT 'My Project',
    subreddits TEXT[] DEFAULT '{}',
    pain_phrases TEXT[] DEFAULT ARRAY[
        'is there a tool', 'need help finding',
        'tired of manually', 'manual process',
        'kills my productivity'
    ],
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);

-- Add foreign keys to posts (now that tables exist)
ALTER TABLE posts ADD CONSTRAINT fk_posts_project
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
ALTER TABLE posts ADD CONSTRAINT fk_posts_user
    FOREIGN KEY (user_id) REFERENCES profiles(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_posts_project ON posts(project_id);
CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);

-- ═══════════════════════════════════════════
-- 4. RLS (users see only their data)
-- ═══════════════════════════════════════════
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own profile" ON profiles
    FOR ALL USING (auth.uid() = id);

CREATE POLICY "Users see own projects" ON projects
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users see all posts" ON posts
    FOR SELECT USING (
        user_id = auth.uid()
        OR user_id IS NULL
    );

-- ═══════════════════════════════════════════
-- 5. Auto-create profile on signup
-- ═══════════════════════════════════════════
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email)
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();
