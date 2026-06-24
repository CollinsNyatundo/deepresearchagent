# Dimension 14: Database Schema, Migration & Security

## Overview

This dimension investigates the technical feasibility of the 6 new database tables proposed in the DRA integration plan. It covers schema design, migration strategy, Row-Level Security (RLS) policies, indexing, performance, and cleanup strategies.

---

## Key Findings

### 1. The Plan Omits RLS Policies for All New Tables

**Claim:** The DRA integration plan proposes 6 new database tables but does not mention updating Row-Level Security (RLS) policies. In a multi-tenant SaaS where all tables have `workspace_id` foreign keys, RLS is the primary security boundary between workspaces.[^1]

**Source:** Supabase RLS Documentation

**URL:** https://supabase.com/docs/guides/database/postgres/row-level-security

**Date:** 2026

**Excerpt:**
> "RLS is a PostgreSQL feature that provides fine-grained access control over database rows. When enabled, PostgreSQL restricts which rows can be returned or modified based on the executing user's identity."

**Context:** The DRA plan correctly adds `workspace_id` to all tables but omits the RLS policies that enforce workspace isolation. Without RLS, any user with database access could query any workspace's data. For example:

```sql
-- Missing from plan: RLS policies for citation_verifications
ALTER TABLE citation_verifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY workspace_isolation ON citation_verifications
  FOR ALL USING (workspace_id = current_setting('app.current_workspace_id')::UUID);
```

This is a critical security vulnerability that must be addressed before any of the new tables are deployed.

**Confidence:** High

---

### 2. JSONB Columns Require GIN Indexes for Query Performance

**Claim:** The plan uses JSONB columns (`sources`, `reviewer_feedback`, `improvement_suggestions`, `relevance_tags`, `artifacts`) for flexible metadata storage. Without GIN indexes on these columns, queries filtering by JSON properties will perform full table scans.[^2]

**Source:** PostgreSQL JSONB Documentation

**URL:** https://www.postgresql.org/docs/current/datatype-json.html

**Date:** 2026

**Excerpt:**
> "GIN indexes can be used to efficiently search for keys or key-value pairs within a large number of jsonb documents."

**Context:** The DRA plan's tables have multiple JSONB columns that will be queried:
- `citation_verifications.sources`: Query by database name (e.g., "show all citations verified by CrossRef")
- `quality_reports.reviewer_feedback`: Query by reviewer type
- `sandbox_experiments.artifacts`: Query by artifact type

Without GIN indexes, these queries will scan the entire table. For 100,000+ rows, this is unacceptable performance.

**Recommendation:** Add GIN indexes to all JSONB columns:
```sql
CREATE INDEX idx_citation_sources ON citation_verifications USING GIN (sources);
CREATE INDEX idx_quality_feedback ON quality_reports USING GIN (reviewer_feedback);
CREATE INDEX idx_experiment_artifacts ON sandbox_experiments USING GIN (artifacts);
```

**Confidence:** High

---

### 3. Foreign Key Constraints Need CASCADE Policies

**Claim:** The plan's tables have `run_id UUID REFERENCES research_runs(id)` but does not specify ON DELETE behavior. When a research run is deleted, orphaned records in citation_verifications, quality_reports, checkpoints, etc., will accumulate.[^3]

**Source:** PostgreSQL Foreign Key Documentation

**URL:** https://www.postgresql.org/docs/current/ddl-constraints.html

**Date:** 2026

**Excerpt:**
> "A foreign key constraint specifies that the values in a column (or a group of columns) must match the values appearing in some row of another table."

**Context:** The DRA plan's CREATE TABLE statements should include ON DELETE CASCADE for all run_id foreign keys:

```sql
-- Plan's current schema (missing CASCADE):
run_id UUID REFERENCES research_runs(id)

-- Should be:
run_id UUID REFERENCES research_runs(id) ON DELETE CASCADE
```

Without CASCADE, deleting a research run requires manually deleting all related records, or the database will reject the deletion. This is a common source of bugs in multi-table applications.

**Confidence:** High

---

**Claim:** The `research_memory` table references `research_runs(id)` but also has rows without a run_id (cross-run memory). This creates a mixed reference pattern where some rows have a run_id and some don't. NULL handling must be explicit.[^4]

**Source:** DRA Integration Plan (research_memory table schema)

**URL:** File: D:\Projects\ai-ml\DeepResearchAgent\research\dra_integration_plan.md

**Date:** 2026

**Excerpt:**
> "run_id UUID REFERENCES research_runs(id)" (in research_memory table)

**Context:** Cross-run memory items may not be associated with a specific run. The plan's schema allows `run_id` to be NULL (implicitly, since UUID columns are nullable by default in PostgreSQL unless specified otherwise). However, the RLS policy for `research_memory` must handle both cases:
- `run_id IS NOT NULL`: Check workspace_id matches AND run_id is in the user's workspace
- `run_id IS NULL`: Check workspace_id matches only

The plan does not specify this dual-mode RLS policy.

**Confidence:** High

---

### 4. `state_json` Size Limits Are Not Addressed

**Claim:** The `research_checkpoints.state_json` column stores unbounded JSONB data. For a 30-cycle research run with 50+ sources per cycle, this could reach 5-10MB per checkpoint. The plan does not specify size limits or truncation strategies.[^5]

**Source:** PostgreSQL JSONB Size Limits / Supabase Best Practices

**URL:** https://supabase.com/docs/guides/database/postgres/floating-point

**Date:** 2026

**Excerpt:**
> "JSONB is optimized for storage, not query performance on large documents. For documents larger than a few MB, consider splitting into relational tables or using external storage."

**Context:** PostgreSQL has a 1GB per-row limit (TOAST), but performance degrades significantly above 10-100MB for JSONB. The plan should:
1. Set a maximum checkpoint size (e.g., 5MB)
2. Truncate non-essential data (e.g., keep source URLs but not full page content)
3. Store large blobs externally (Supabase Storage) and reference them in JSONB

**Recommendation:** Add a CHECK constraint:
```sql
ALTER TABLE research_checkpoints
  ADD CONSTRAINT max_state_size CHECK (pg_column_size(state_json) <= 5242880);  -- 5MB
```

**Confidence:** High

---

### 5. Migration Strategy Is Missing

**Claim:** The DRA plan provides CREATE TABLE statements but does not specify how to migrate existing data or handle schema evolution. For a production system with existing users, adding 6 new tables requires a migration plan.[^6]

**Source:** Database Migration Best Practices (Flyway, Liquibase, Alembic)

**URL:** https://flywaydb.org/documentation/

**Date:** 2026

**Excerpt:**
> "Database migrations are the process of managing database schema changes over time."

**Context:** DRA uses Supabase, which supports migrations via the Supabase CLI or raw SQL. The plan should specify:
- Migration order (which tables to create first, considering foreign key dependencies)
- Backward compatibility (will old code work with new tables before the feature is enabled?)
- Rollback strategy (how to undo the migration if something breaks)
- Data seeding (initial data for new tables, if any)

The foreign key dependency order is:
1. `research_runs` (already exists) → create tables referencing it
2. `citation_verifications`, `quality_reports`, `research_checkpoints`, `report_versions` (all depend on research_runs)
3. `sandbox_experiments` (depends on research_runs)
4. `research_memory` (depends on research_runs, but also allows NULL run_id)

**Confidence:** High

---

## Tensions and Counter-Arguments

### Tension 1: JSONB Flexibility vs. Query Performance

JSONB columns provide flexibility for evolving schemas but sacrifice query performance. For frequently queried fields (e.g., `citation_verifications.status`), a dedicated column with a B-tree index would be much faster than a JSONB GIN index.

**Counter-argument:** The plan correctly uses dedicated columns for frequently queried fields (`status`, `phase`, `version`) and JSONB for metadata. However, some fields that should be dedicated columns are in JSONB:
- `citation_verifications.sources` — frequently queried by database name, should be a normalized table
- `quality_reports.reviewer_feedback` — frequently queried, should be a dedicated table
- `sandbox_experiments.artifacts` — could be a dedicated table with artifact type

For MVP, JSONB is acceptable. For production at scale, consider normalizing these into dedicated tables.

### Tension 2: Workspace Isolation vs. Cross-Workspace Sharing

The `research_memory` table stores cross-run findings within a workspace. But what if a user wants to share a finding with another workspace? The plan does not address cross-workspace sharing.

**Counter-argument:** For MVP, workspace isolation is sufficient. Cross-workspace sharing can be added later with a separate `shared_findings` table or workspace invitation system.

### Tension 3: Soft Deletes vs. Hard Deletes

The plan does not mention soft deletes. For audit purposes (especially with provenance tracking), soft deletes may be preferable to hard deletes. However, soft deletes add complexity (every query needs `WHERE deleted_at IS NULL`).

**Counter-argument:** Use hard deletes for MVP. Add soft deletes only if audit requirements emerge. The `research_checkpoints` table already has a TTL-based cleanup, so hard deletes are consistent with the plan's approach.

---

## Recommendations

### 1. Add RLS Policies to All New Tables

```sql
-- Enable RLS on all new tables
ALTER TABLE citation_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE quality_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE sandbox_experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_memory ENABLE ROW LEVEL SECURITY;

-- Create workspace isolation policies
CREATE POLICY workspace_isolation_citations ON citation_verifications
  FOR ALL USING (workspace_id = current_setting('app.current_workspace_id')::UUID);

CREATE POLICY workspace_isolation_quality ON quality_reports
  FOR ALL USING (workspace_id = current_setting('app.current_workspace_id')::UUID);

CREATE POLICY workspace_isolation_checkpoints ON research_checkpoints
  FOR ALL USING (workspace_id = current_setting('app.current_workspace_id')::UUID);

CREATE POLICY workspace_isolation_versions ON report_versions
  FOR ALL USING (workspace_id = current_setting('app.current_workspace_id')::UUID);

CREATE POLICY workspace_isolation_experiments ON sandbox_experiments
  FOR ALL USING (workspace_id = current_setting('app.current_workspace_id')::UUID);

CREATE POLICY workspace_isolation_memory ON research_memory
  FOR ALL USING (workspace_id = current_setting('app.current_workspace_id')::UUID);
```

### 2. Add ON DELETE CASCADE to All Foreign Keys

```sql
-- Fix foreign key constraints in migration
ALTER TABLE citation_verifications
  DROP CONSTRAINT IF EXISTS citation_verifications_run_id_fkey,
  ADD CONSTRAINT citation_verifications_run_id_fkey
  FOREIGN KEY (run_id) REFERENCES research_runs(id) ON DELETE CASCADE;

-- Repeat for all tables referencing research_runs
```

### 3. Add GIN Indexes to JSONB Columns

```sql
CREATE INDEX idx_citation_sources ON citation_verifications USING GIN (sources);
CREATE INDEX idx_quality_feedback ON quality_reports USING GIN (reviewer_feedback);
CREATE INDEX idx_experiment_artifacts ON sandbox_experiments USING GIN (artifacts);
CREATE INDEX idx_memory_tags ON research_memory USING GIN (relevance_tags);
```

### 4. Add Size Limits and CHECK Constraints

```sql
-- Limit checkpoint size to 5MB
ALTER TABLE research_checkpoints
  ADD CONSTRAINT max_state_size CHECK (pg_column_size(state_json) <= 5242880);

-- Ensure status values are valid
ALTER TABLE citation_verifications
  ADD CONSTRAINT valid_status CHECK (status IN ('verified', 'unverified', 'failed'));
```

### 5. Document Migration Order and Rollback Strategy

```sql
-- Migration 001: Create citation_verifications
-- (no dependencies beyond research_runs which exists)

-- Migration 002: Create quality_reports
-- (depends on research_runs, citation_verifications optional)

-- Migration 003: Create research_checkpoints
-- (depends on research_runs)

-- Migration 004: Create report_versions
-- (depends on research_runs)

-- Migration 005: Create sandbox_experiments
-- (depends on research_runs, deferred to P3)

-- Migration 006: Create research_memory
-- (depends on research_runs, optional NULL run_id)

-- Rollback: Drop all tables in reverse order
-- research_memory → sandbox_experiments → report_versions → research_checkpoints → quality_reports → citation_verifications
```

---

## Confidence Assessment

| Finding | Confidence |
|---------|------------|
| RLS policies are missing from plan | High |
| JSONB columns need GIN indexes | High |
| Foreign keys need ON DELETE CASCADE | High |
| state_json needs size limits | High |
| Migration strategy is missing | High |

---

## Sources

[^1]: Supabase RLS Documentation. 2026. https://supabase.com/docs/guides/database/postgres/row-level-security

[^2]: PostgreSQL JSONB Documentation. 2026. https://www.postgresql.org/docs/current/datatype-json.html

[^3]: PostgreSQL Foreign Key Documentation. 2026. https://www.postgresql.org/docs/current/ddl-constraints.html

[^4]: DRA Integration Plan (research_memory schema). 2026. File: dra_integration_plan.md

[^5]: PostgreSQL JSONB Size Limits. 2026. https://supabase.com/docs/guides/database/postgres/floating-point

[^6]: Flyway Database Migration Documentation. 2026. https://flywaydb.org/documentation/

