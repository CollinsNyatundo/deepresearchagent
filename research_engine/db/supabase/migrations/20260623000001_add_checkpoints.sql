-- Checkpoints Table (Track C: Checkpoints & Resume)
-- Created: 2026-06-23

-- 1. Checkpoints Table
CREATE TABLE checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES research_runs(id) ON DELETE CASCADE NOT NULL,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    phase TEXT NOT NULL,
    state_json JSONB NOT NULL,
    size_bytes INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Index for fast lookup
CREATE INDEX idx_checkpoints_run_id ON checkpoints(run_id);
CREATE INDEX idx_checkpoints_workspace_id ON checkpoints(workspace_id);
CREATE INDEX idx_checkpoints_created_at ON checkpoints(created_at);

-- 3. Enable RLS
ALTER TABLE checkpoints ENABLE ROW LEVEL SECURITY;

-- 4. RLS Policy: workspace isolation
CREATE POLICY workspace_isolation_checkpoints ON checkpoints
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = checkpoints.workspace_id
            AND workspace_members.user_id = auth.uid()
        )
    );
