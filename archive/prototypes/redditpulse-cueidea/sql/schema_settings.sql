-- RedditPulse — User Settings Schema (FIXED)
-- Run this in Supabase SQL Editor
-- If you already ran the old version, run the DROP first:
-- DROP TABLE IF EXISTS user_settings;

CREATE TABLE IF NOT EXISTS user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    gemini_api_key TEXT,
    groq_api_key TEXT,
    openai_api_key TEXT,
    notification_email BOOLEAN DEFAULT true,
    scan_limit INTEGER DEFAULT 10,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_settings_user ON user_settings(user_id);

-- RLS — must have separate SELECT and INSERT/UPDATE policies
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

-- Drop old policy if exists
DROP POLICY IF EXISTS "Users manage own settings" ON user_settings;

-- Users can READ their own settings
CREATE POLICY "Users read own settings" ON user_settings
    FOR SELECT USING (auth.uid() = user_id);

-- Users can INSERT their own settings
CREATE POLICY "Users insert own settings" ON user_settings
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Users can UPDATE their own settings
CREATE POLICY "Users update own settings" ON user_settings
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can DELETE their own settings
CREATE POLICY "Users delete own settings" ON user_settings
    FOR DELETE USING (auth.uid() = user_id);
