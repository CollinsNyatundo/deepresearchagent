# DeepResearchAgent — Database Schema Reference

> **Last Updated:** 2026-06-26
> **Source:** `supabase/migrations/combined_migration.sql`
> **Database:** PostgreSQL 15 (Supabase)

---

## Table of Contents

1. [Extensions](#1-extensions)
2. [Tables](#2-tables)
3. [Indexes](#3-indexes)
4. [Row-Level Security Policies](#4-row-level-security-policies)
5. [Custom Functions and RPCs](#5-custom-functions-and-rpcs)
6. [Triggers](#6-triggers)
7. [Migration History](#7-migration-history)

---

## 1. Extensions

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- UUID generation
CREATE EXTENSION IF NOT EXISTS "vector";       -- pgvector (1536-dim embeddings)
```

---

## 2. Tables

### `workspaces`

Registry of all workspaces (multi-tenant root entity).

```sql
CREATE TABLE workspaces (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    metadata    JSONB DEFAULT '{}'
);
```

---

### `workspace_members`

Links users to workspaces (many-to-many, composite PK).

```sql
CREATE TABLE workspace_members (
    workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL,                 -- references auth.users
    role          TEXT DEFAULT 'member',          -- 'owner' | 'admin' | 'member'
    joined_at     TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (workspace_id, user_id)
);
```

---

### `research_runs`

One record per research run. Stores the full report, mindmap data, and KG.

```sql
CREATE TABLE research_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL,
    query           TEXT NOT NULL,
    status          TEXT DEFAULT 'pending',       -- see ResearchState enum
    report          TEXT,                         -- Markdown report text
    citations       JSONB DEFAULT '[]',           -- array of citation objects
    model           TEXT,                         -- LLM model used
    depth           INTEGER DEFAULT 5,            -- research depth (1–5)
    cycle_count     INTEGER DEFAULT 0,
    search_provider TEXT,
    plan            JSONB,                        -- research plan (decomposed queries)
    mindmap         JSONB,                        -- G6 mindmap data
    knowledge_graph JSONB,                        -- full KG JSON
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);
```

**Key indexes:**
```sql
CREATE INDEX idx_research_runs_workspace ON research_runs(workspace_id);
CREATE INDEX idx_research_runs_status ON research_runs(status);
CREATE INDEX idx_research_runs_created ON research_runs(created_at DESC);
```

---

### `graph_nodes`

Knowledge graph nodes with pgvector embeddings (1536 dimensions, OpenAI-compatible).

```sql
CREATE TABLE graph_nodes (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id        UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    node_id       TEXT NOT NULL,                  -- internal graph identifier
    label         TEXT NOT NULL,
    type          TEXT DEFAULT 'concept',          -- function|class|concept|paper|diagram
    community     INTEGER DEFAULT 0,               -- Leiden community ID
    degree        INTEGER DEFAULT 0,               -- edge count
    is_god_node   BOOLEAN DEFAULT FALSE,           -- top-N highest degree
    provenance    TEXT DEFAULT 'EXTRACTED',        -- EXTRACTED|INFERRED|AMBIGUOUS
    confidence    FLOAT DEFAULT 1.0,               -- 0–1
    embedding     vector(1536),                    -- pgvector embedding
    properties    JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

---

### `graph_edges`

Directed edges between knowledge graph nodes.

```sql
CREATE TABLE graph_edges (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id        UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    source        TEXT NOT NULL,                  -- source node_id
    target        TEXT NOT NULL,                  -- target node_id
    type          TEXT DEFAULT 'related_to',      -- calls|imports|rationale_for|semantically_similar_to
    weight        FLOAT DEFAULT 1.0,
    is_surprise   BOOLEAN DEFAULT FALSE,          -- cross-community edge
    properties    JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

---

### `notes`

Personal notes with full-text search and wiki-link support.

```sql
CREATE TABLE notes (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL,
    title         TEXT NOT NULL DEFAULT '',
    content       TEXT DEFAULT '',
    tags          JSONB DEFAULT '[]',             -- string array
    is_pinned     BOOLEAN DEFAULT FALSE,
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english',
            coalesce(title, '') || ' ' || coalesce(content, ''))
    ) STORED,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);
```

> `search_vector` is automatically kept in sync via `GENERATED ALWAYS AS` — no trigger needed.

---

### `documents`

OpenKB document metadata. Actual document content lives on the local filesystem at `openkb/{workspace_id}/`.

```sql
CREATE TABLE documents (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL,
    filename      TEXT NOT NULL,
    original_name TEXT NOT NULL,
    file_size     BIGINT,
    mime_type     TEXT,
    status        TEXT DEFAULT 'processing',      -- processing|ready|error
    chunk_count   INTEGER DEFAULT 0,
    metadata      JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);
```

---

### `document_tags`

Many-to-many tagging for documents.

```sql
CREATE TABLE document_tags (
    document_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tag           TEXT NOT NULL,
    PRIMARY KEY (document_id, tag)
);
```

---

### `citation_verifications`

Citation cross-verification results linked to a research run.

```sql
CREATE TABLE citation_verifications (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id        UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    url           TEXT NOT NULL,
    claim         TEXT,
    is_verified   BOOLEAN,
    confidence    FLOAT,
    verification_source TEXT,
    metadata      JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 3. Indexes

```sql
-- research_runs
CREATE INDEX idx_research_runs_workspace ON research_runs(workspace_id);
CREATE INDEX idx_research_runs_status    ON research_runs(status);
CREATE INDEX idx_research_runs_created   ON research_runs(created_at DESC);

-- graph_nodes
CREATE INDEX idx_graph_nodes_run         ON graph_nodes(run_id);
CREATE INDEX idx_graph_nodes_workspace   ON graph_nodes(workspace_id);
CREATE INDEX idx_graph_nodes_community   ON graph_nodes(community);
CREATE INDEX idx_graph_nodes_embedding   ON graph_nodes USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);   -- pgvector approximate nearest neighbor

-- graph_edges
CREATE INDEX idx_graph_edges_run         ON graph_edges(run_id);
CREATE INDEX idx_graph_edges_source      ON graph_edges(source);
CREATE INDEX idx_graph_edges_target      ON graph_edges(target);

-- notes
CREATE INDEX idx_notes_workspace         ON notes(workspace_id);
CREATE INDEX idx_notes_updated           ON notes(updated_at DESC);
CREATE INDEX idx_notes_search            ON notes USING GIN(search_vector);

-- documents
CREATE INDEX idx_documents_workspace     ON documents(workspace_id);
CREATE INDEX idx_documents_status        ON documents(status);

-- citation_verifications
CREATE INDEX idx_citations_run           ON citation_verifications(run_id);
```

---

## 4. Row-Level Security Policies

All tables have `ENABLE ROW LEVEL SECURITY`. The universal workspace isolation pattern:

```sql
-- Template: SELECT policy
CREATE POLICY "workspace_members_can_select"
ON <table> FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM workspace_members wm
        WHERE wm.workspace_id = <table>.workspace_id
          AND wm.user_id = auth.uid()
    )
);

-- Template: INSERT policy  
CREATE POLICY "workspace_members_can_insert"
ON <table> FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM workspace_members wm
        WHERE wm.workspace_id = NEW.workspace_id
          AND wm.user_id = auth.uid()
    )
);

-- Template: UPDATE policy
CREATE POLICY "workspace_members_can_update"
ON <table> FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM workspace_members wm
        WHERE wm.workspace_id = <table>.workspace_id
          AND wm.user_id = auth.uid()
    )
);

-- Template: DELETE policy
CREATE POLICY "workspace_members_can_delete"
ON <table> FOR DELETE
USING (
    EXISTS (
        SELECT 1 FROM workspace_members wm
        WHERE wm.workspace_id = <table>.workspace_id
          AND wm.user_id = auth.uid()
    )
);
```

### Special Case: `workspaces` and `workspace_members`

```sql
-- workspace_members: users can SELECT their own memberships
CREATE POLICY "users_can_see_own_memberships"
ON workspace_members FOR SELECT
USING (user_id = auth.uid());

-- workspaces: accessible if member
CREATE POLICY "members_can_see_workspaces"
ON workspaces FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM workspace_members
        WHERE workspace_members.workspace_id = workspaces.id
          AND workspace_members.user_id = auth.uid()
    )
);
```

> [!IMPORTANT]
> The backend uses the **service_role** key which bypasses RLS entirely.
> RLS is enforced at the Supabase edge for direct client (anon key) access from the browser.

---

## 5. Custom Functions and RPCs

### `match_graph_nodes`

Cosine similarity search over knowledge graph node embeddings.

```sql
CREATE OR REPLACE FUNCTION match_graph_nodes(
    query_embedding  vector(1536),
    match_threshold  float DEFAULT 0.7,
    match_count      int   DEFAULT 10
)
RETURNS TABLE (
    id          uuid,
    run_id      uuid,
    workspace_id uuid,
    node_id     text,
    label       text,
    type        text,
    community   int,
    degree      int,
    is_god_node boolean,
    confidence  float,
    similarity  float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id, run_id, workspace_id, node_id, label, type,
        community, degree, is_god_node, confidence,
        1 - (embedding <=> query_embedding) AS similarity
    FROM graph_nodes
    WHERE 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
$$;
```

**Usage (Python):**
```python
result = await asyncio.to_thread(
    lambda: supabase.rpc("match_graph_nodes", {
        "query_embedding": embedding_list,
        "match_threshold": 0.75,
        "match_count": 10,
    }).execute()
)
```

---

## 6. Triggers

### `updated_at` Auto-Update

Applied to `workspaces`, `research_runs`, `notes`, `documents`:

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_<table>_updated_at
    BEFORE UPDATE ON <table>
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

## 7. Migration History

| Migration File | Tables Added | Description |
|----------------|-------------|-------------|
| `combined_migration.sql` (part 1) | `workspaces`, `workspace_members`, `research_runs`, `graph_nodes`, `graph_edges` | Initial schema + pgvector + RLS |
| `combined_migration.sql` (part 2) | `notes`, `documents`, `document_tags` | Notes and Documents module support |
| `combined_migration.sql` (part 3) | `citation_verifications` | Citation verification system |

### Applying Migrations

1. Open the Supabase SQL Editor for your project
2. Copy the contents of `supabase/migrations/combined_migration.sql`
3. Run the entire migration in one transaction
4. Verify with:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
-- Expected: citation_verifications, document_tags, documents, graph_edges,
--           graph_nodes, notes, research_runs, workspace_members, workspaces
```

---

*Generated: 2026-06-26 | Source: `supabase/migrations/combined_migration.sql`*
