-- Fix: user_ai_config schema issues
-- 1. The code falls back to writing plain 'api_key' but that column doesn't exist.
-- 2. The 'api_key_encrypted' column has NOT NULL, so plaintext inserts fail.

-- Drop NOT NULL on the encrypted column (plaintext fallback doesn't use it)
ALTER TABLE user_ai_config ALTER COLUMN api_key_encrypted DROP NOT NULL;

-- Add the plain api_key column
ALTER TABLE user_ai_config
ADD COLUMN IF NOT EXISTS api_key TEXT DEFAULT '';

-- Done. Settings page can now save API keys.
