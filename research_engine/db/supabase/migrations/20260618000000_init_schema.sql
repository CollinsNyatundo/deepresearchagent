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
