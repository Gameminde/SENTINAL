-- RedditPulse — Idea Validations table
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS idea_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    idea_text TEXT NOT NULL,
    model TEXT DEFAULT 'gemini',
    depth TEXT DEFAULT 'quick',
    status TEXT DEFAULT 'starting',

    -- Phase 1: AI Decomposition output
    extracted_keywords TEXT[] DEFAULT '{}',
    extracted_competitors TEXT[] DEFAULT '{}',
    extracted_audience TEXT,
    pain_hypothesis TEXT,

    -- Phase 2: Scraping progress
    posts_found INTEGER DEFAULT 0,
    posts_filtered INTEGER DEFAULT 0,
    posts_analyzed INTEGER DEFAULT 0,

    -- Phase 3: AI Synthesis output
    verdict TEXT,
    confidence INTEGER DEFAULT 0,
    report JSONB DEFAULT '{}',

    -- Error tracking
    error TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_validations_user ON idea_validations(user_id);
CREATE INDEX IF NOT EXISTS idx_validations_created ON idea_validations(created_at DESC);

-- RLS
ALTER TABLE idea_validations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own validations" ON idea_validations
    FOR ALL USING (auth.uid() = user_id);
