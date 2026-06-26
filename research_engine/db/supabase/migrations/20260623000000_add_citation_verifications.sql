-- Citation Verifications Table (Track A: Cross-Verification Integration)
-- Created: 2026-06-23
-- Provides persistent storage for citation verification results per research run

-- 1. Citation Verifications Table
CREATE TABLE citation_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES research_runs(id) ON DELETE CASCADE NOT NULL,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    citation_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'failed',  -- verified | unverified | failed
    found BOOLEAN NOT NULL DEFAULT FALSE,
    title TEXT,
    authors TEXT[] DEFAULT '{}',
    year INT,
    doi TEXT,
    url TEXT,
    confidence FLOAT DEFAULT 0.0,
    sources INT DEFAULT 0,
    databases TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Index for fast lookup by run_id
CREATE INDEX idx_citation_verifications_run_id ON citation_verifications(run_id);
CREATE INDEX idx_citation_verifications_workspace_id ON citation_verifications(workspace_id);
CREATE INDEX idx_citation_verifications_doi ON citation_verifications(doi);

-- 3. Enable Row-Level Security
ALTER TABLE citation_verifications ENABLE ROW LEVEL SECURITY;

-- 4. RLS Policy: workspace isolation
-- Users can only access citation_verifications for workspaces they are members of
CREATE POLICY workspace_isolation_citations ON citation_verifications
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = citation_verifications.workspace_id
            AND workspace_members.user_id = auth.uid()
        )
    );

-- 5. Trigger to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_citation_verifications_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_citation_verifications_updated_at
    BEFORE UPDATE ON citation_verifications
    FOR EACH ROW
    EXECUTE FUNCTION update_citation_verifications_updated_at();
