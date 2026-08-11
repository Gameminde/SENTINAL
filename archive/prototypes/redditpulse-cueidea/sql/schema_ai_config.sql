-- RedditPulse — User AI Configuration table (with encryption)
-- Run this in Supabase SQL Editor

-- Enable pgcrypto for encryption
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Drop old table if exists (no data loss since this is new)
DROP TABLE IF EXISTS user_ai_config;

CREATE TABLE user_ai_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    api_key_encrypted BYTEA NOT NULL,     -- encrypted with pgp_sym_encrypt
    selected_model TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 1 CHECK (priority BETWEEN 1 AND 10),
    endpoint_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_config_user ON user_ai_config(user_id);

-- RLS
ALTER TABLE user_ai_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own AI config" ON user_ai_config
    FOR ALL USING (auth.uid() = user_id);

-- Helper: encrypt key
-- Usage: INSERT INTO user_ai_config (..., api_key_encrypted) VALUES (..., pgp_sym_encrypt('sk-xxx', 'your-app-secret'))
-- Read:  SELECT pgp_sym_decrypt(api_key_encrypted, 'your-app-secret') as api_key FROM user_ai_config
