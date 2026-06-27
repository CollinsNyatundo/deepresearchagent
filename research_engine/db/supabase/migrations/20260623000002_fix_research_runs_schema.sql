-- Migration: Add missing columns to research_runs and create comprehensive schema fixes
-- Run after: 20260618000001_add_notes_and_documents.sql

-- 1. Add missing columns to research_runs that the API expects
ALTER TABLE research_runs 
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS depth INT DEFAULT 1,
    ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'web',
    ADD COLUMN IF NOT EXISTS plan JSONB,
    ADD COLUMN IF NOT EXISTS mindmap JSONB,
    ADD COLUMN IF NOT EXISTS knowledge_graph JSONB,
    ADD COLUMN IF NOT EXISTS citations JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS sources JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS total_cycles INT DEFAULT 0;

-- 2. Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_research_runs_user_id ON research_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_research_runs_status ON research_runs(status);
CREATE INDEX IF NOT EXISTS idx_research_runs_started_at ON research_runs(started_at);

-- 3. Add trigger to auto-update started_at on status change to initializing
CREATE OR REPLACE FUNCTION set_research_runs_started_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'initializing' AND NEW.started_at IS NULL THEN
        NEW.started_at = timezone('utc'::text, now());
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_set_research_runs_started_at ON research_runs;
CREATE TRIGGER trigger_set_research_runs_started_at
    BEFORE INSERT OR UPDATE ON research_runs
    FOR EACH ROW
    EXECUTE FUNCTION set_research_runs_started_at();

-- 4. Add RLS policy for user_id (users can only access their own runs within their workspace)
CREATE POLICY IF NOT EXISTS access_runs_user_id ON research_runs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = research_runs.workspace_id
            AND workspace_members.user_id = auth.uid()
        )
    );
