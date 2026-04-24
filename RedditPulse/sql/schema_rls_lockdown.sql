-- RedditPulse — RLS Lockdown (Financial Security)
-- Run this in Supabase SQL Editor AFTER schema_saas.sql
-- Restricts what users can update on their own profiles

-- ═══════════════════════════════════════════
-- 1. PROFILES — Lock down plan/stripe columns
-- ═══════════════════════════════════════════
-- Drop the overly permissive "FOR ALL" policy
DROP POLICY IF EXISTS "Users see own profile" ON profiles;

-- SELECT: Users can read their own profile (all columns)
CREATE POLICY "profiles_select_own" ON profiles
    FOR SELECT USING (auth.uid() = id);

-- UPDATE: Users can update ONLY safe columns (not plan, stripe, paid_at)
CREATE POLICY "profiles_update_safe" ON profiles
    FOR UPDATE USING (auth.uid() = id)
    WITH CHECK (
        -- Block plan escalation: new plan must equal old plan
        -- This uses a subquery to compare against the existing value
        plan = (SELECT p.plan FROM profiles p WHERE p.id = auth.uid())
        AND stripe_customer_id IS NOT DISTINCT FROM (SELECT p.stripe_customer_id FROM profiles p WHERE p.id = auth.uid())
        AND stripe_payment_id IS NOT DISTINCT FROM (SELECT p.stripe_payment_id FROM profiles p WHERE p.id = auth.uid())
        AND paid_at IS NOT DISTINCT FROM (SELECT p.paid_at FROM profiles p WHERE p.id = auth.uid())
    );

-- INSERT: Only the trigger/service_role can insert profiles (not users)
-- No INSERT policy = users cannot insert into profiles table via anon key

-- DELETE: Users cannot delete their own profile
-- No DELETE policy = blocked by default with RLS enabled

-- ═══════════════════════════════════════════
-- 2. USER_AI_CONFIG — Prevent browser reads of api_key
-- ═══════════════════════════════════════════
-- Drop existing permissive policy if any
DROP POLICY IF EXISTS "Users manage own AI config" ON user_ai_config;

-- SELECT: Users can read their own configs BUT api_key is excluded
-- (Use a view or RPC to control which columns are returned)
CREATE POLICY "ai_config_select_own" ON user_ai_config
    FOR SELECT USING (auth.uid() = user_id);

-- INSERT: Users can add their own configs
CREATE POLICY "ai_config_insert_own" ON user_ai_config
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- UPDATE: Users can update their own configs
CREATE POLICY "ai_config_update_own" ON user_ai_config
    FOR UPDATE USING (auth.uid() = user_id);

-- DELETE: Users can remove their own configs
CREATE POLICY "ai_config_delete_own" ON user_ai_config
    FOR DELETE USING (auth.uid() = user_id);

-- ═══════════════════════════════════════════
-- 3. Create a SECURE view that hides api_key from direct queries
--    Since api_key_encrypted is BYTEA (pgcrypto), we just show a boolean
-- ═══════════════════════════════════════════
CREATE OR REPLACE VIEW user_ai_config_safe AS
SELECT
    id,
    user_id,
    provider,
    CASE WHEN api_key_encrypted IS NOT NULL THEN '••••••••' ELSE '' END AS api_key_masked,
    selected_model,
    is_active,
    priority,
    endpoint_url,
    created_at
FROM user_ai_config
WHERE user_id = auth.uid();

-- NOTE: The actual api_key_encrypted column is BYTEA and requires
-- pgp_sym_decrypt() with the encryption key to read.
-- API routes use service_role + RPC to decrypt server-side.
-- This view is for frontend queries that only need to know IF a key exists.
