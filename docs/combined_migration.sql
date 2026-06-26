-- ===== Migration: 20260618000000_init_schema.sql =====
-- 1. Enable UUID and Vector Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Workspaces Table
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Workspace Members Table (linking user accounts to workspaces)
CREATE TABLE workspace_members (
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL, -- references auth.users in Supabase
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    PRIMARY KEY (workspace_id, user_id)
);

-- 4. Research Runs Table
CREATE TABLE research_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
    query TEXT NOT NULL,
    model_used TEXT,
    report TEXT,
    status TEXT NOT NULL DEFAULT 'initializing',
    progress INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 5. Graph Nodes Table
CREATE TABLE graph_nodes (
    run_id UUID REFERENCES research_runs(id) ON DELETE CASCADE NOT NULL,
    id TEXT NOT NULL,
    label TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'concept',
    community INT DEFAULT 0,
    degree INT DEFAULT 0,
    is_god_node BOOLEAN DEFAULT FALSE,
    provenance TEXT NOT NULL DEFAULT 'EXTRACTED',
    confidence FLOAT DEFAULT 1.0,
    summary TEXT,
    file_path TEXT,
    embedding vector(1536), -- 1536-dimensional embeddings
    PRIMARY KEY (run_id, id)
);

-- 6. Graph Edges Table
CREATE TABLE graph_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES research_runs(id) ON DELETE CASCADE NOT NULL,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'semantically_similar_to',
    provenance TEXT NOT NULL DEFAULT 'EXTRACTED',
    confidence FLOAT DEFAULT 1.0,
    label TEXT,
    FOREIGN KEY (run_id, source) REFERENCES graph_nodes(run_id, id) ON DELETE CASCADE,
    FOREIGN KEY (run_id, target) REFERENCES graph_nodes(run_id, id) ON DELETE CASCADE
);

-- 7. Configure Row-Level Security (RLS)
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_edges ENABLE ROW LEVEL SECURITY;

-- 8. RLS Policies

-- workspaces: select if member
CREATE POLICY select_workspaces ON workspaces
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = workspaces.id
            AND workspace_members.user_id = auth.uid()
        )
    );

-- workspace_members: select if user matches auth.uid()
CREATE POLICY select_members ON workspace_members
    FOR SELECT USING (user_id = auth.uid());

-- research_runs: access restricted to workspace members
CREATE POLICY access_runs ON research_runs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = research_runs.workspace_id
            AND workspace_members.user_id = auth.uid()
        )
    );

-- graph_nodes: access restricted to workspace members via research run association
CREATE POLICY access_nodes ON graph_nodes
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM research_runs
            JOIN workspace_members ON workspace_members.workspace_id = research_runs.workspace_id
            WHERE research_runs.id = graph_nodes.run_id
            AND workspace_members.user_id = auth.uid()
        )
    );

-- graph_edges: access restricted to workspace members via research run association
CREATE POLICY access_edges ON graph_edges
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM research_runs
            JOIN workspace_members ON workspace_members.workspace_id = research_runs.workspace_id
            WHERE research_runs.id = graph_edges.run_id
            AND workspace_members.user_id = auth.uid()
        )
    );

-- 9. Custom RPC Function for Cosine Similarity Matching of Graph Nodes
CREATE OR REPLACE FUNCTION match_graph_nodes (
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id TEXT,
  label TEXT,
  type TEXT,
  community INT,
  confidence FLOAT,
  summary TEXT,
  file_path TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    graph_nodes.id,
    graph_nodes.label,
    graph_nodes.type,
    graph_nodes.community,
    graph_nodes.confidence,
    graph_nodes.summary,
    graph_nodes.file_path,
    (1 - (graph_nodes.embedding <=> query_embedding))::float AS similarity
  FROM graph_nodes
  WHERE (1 - (graph_nodes.embedding <=> query_embedding)) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;


-- ===== Migration: 20260618000001_add_notes_and_documents.sql =====
-- Migration: Add notes and documents tables
-- Run after: 20260618000000_init_schema.sql

-- 10. Notes Table (for the Notes module)
CREATE TABLE notes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title VARCHAR(500) NOT NULL,
  content TEXT NOT NULL DEFAULT '',
  tags JSONB DEFAULT '[]'::jsonb,
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE INDEX idx_notes_workspace ON notes(workspace_id);
CREATE INDEX idx_notes_user ON notes(user_id);
CREATE INDEX idx_notes_updated ON notes(workspace_id, updated_at DESC);

-- Full-text search index for notes
ALTER TABLE notes ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))) STORED;
CREATE INDEX idx_notes_search ON notes USING GIN(search_vector);

-- 11. Documents Table (metadata for OpenKB documents)
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  filename VARCHAR(500) NOT NULL,
  file_path TEXT NOT NULL,
  file_size BIGINT,
  mime_type VARCHAR(100),
  status VARCHAR(50) DEFAULT 'uploaded',
  page_count INTEGER,
  indexed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE INDEX idx_documents_workspace ON documents(workspace_id);

-- 12. Document Tags (many-to-many)
CREATE TABLE document_tags (
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  tag VARCHAR(100) NOT NULL,
  PRIMARY KEY (document_id, tag)
);

-- 13. RLS Policies for new tables

ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_tags ENABLE ROW LEVEL SECURITY;

-- notes: access restricted to workspace members
CREATE POLICY access_notes ON notes
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM workspace_members
      WHERE workspace_members.workspace_id = notes.workspace_id
      AND workspace_members.user_id = auth.uid()
    )
  );

-- documents: access restricted to workspace members
CREATE POLICY access_documents ON documents
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM workspace_members
      WHERE workspace_members.workspace_id = documents.workspace_id
      AND workspace_members.user_id = auth.uid()
    )
  );

-- document_tags: access via document association
CREATE POLICY access_document_tags ON document_tags
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM documents
      JOIN workspace_members ON workspace_members.workspace_id = documents.workspace_id
      WHERE documents.id = document_tags.document_id
      AND workspace_members.user_id = auth.uid()
    )
  );


-- ===== Migration: 20260623000000_add_citation_verifications.sql =====
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
