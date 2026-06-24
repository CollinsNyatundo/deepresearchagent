---
title: "feat: Transition to cloud-supported architecture using Supabase and Render"
type: feat
status: active
date: 2026-06-18
origin: docs/brainstorms/2026-06-18-cloud-architecture-transition-requirements.md
---

# feat: Transition to cloud-supported architecture using Supabase and Render

## Summary

This plan outlines the technical transition of Deep Research Agent (DRE) from a local-only model to a split-platform cloud architecture. Supabase hosts user accounts, workspaces, relational graph storage, and `pgvector` search, while Render hosts custom containerized worker instances executing Playwright/Camoufox background scrapers.

---

## Problem Frame

Converting DRE into a cloud-native SaaS requires solving collaborative state synchronization (shared graphs and workspaces) and securing execution boundaries without exceeding serverless resource limits. Because research cycles can run for up to 15 minutes and require heavy browser binaries (Camoufox), standard serverless functions are inadequate. A split control-plane/worker stack solves this limitation.

---

## Requirements

### R-IDs Traceability (from origin: docs/brainstorms/2026-06-18-cloud-architecture-transition-requirements.md)

**User Authentication & Workspaces**
- R1. The system must support email/password and OAuth authentication using Supabase Auth.
- R2. The system must partition all research runs, reports, and knowledge graphs under a Workspace model, allowing multiple users to view and share data within the same workspace.
- R3. The system must enforce Row-Level Security (RLS) policies on all tables so that users can only access graphs and reports belonging to their active workspace.

**Graph & Vector Storage**
- R4. The database must store the Graphify knowledge graph entities and edges in relational Postgres tables.
- R5. The database must store semantic embeddings for knowledge graph nodes using `pgvector` columns.
- R6. The backend must provide a unified SQL interface to query semantically similar nodes and their adjacent relations within a single database request.

**Background Worker Execution**
- R7. The system must orchestrate background research tasks using Supabase Database Webhooks as the primary stateless event trigger, with a fallback option for an external message queue if task queuing or rate-limiting guarantees are required.
- R8. The worker must run as a persistent container on Render, configured with Playwright and the Camoufox browser binary.
- R9. The worker must stream real-time research state transitions (e.g., planning, scraping, reflecting) back to the Supabase database, which broadcasts them to the frontend via Supabase Realtime.
- R10. The Render worker endpoint must validate a secure signature or shared token for all incoming webhook requests to prevent unauthorized research execution.

---

## Key Technical Decisions

- **Supabase PostgreSQL Schema (KTD-1):** Store graph nodes and edges as distinct tables rather than raw JSON blobs to allow fast relational JOINs and proper database indexes. Node embeddings will utilize the `pgvector` data type and `ivfflat` or `hnsw` indexing.
- **Shared Secret Signature Validation (KTD-2):** Secure communication between Supabase and Render using HMAC-SHA256 signatures passed in the webhook authorization header. The Render worker will reject any payload that fails signature validation.
- **Docker-packaged Worker (KTD-3):** Package the Python runtime along with `camoufox` and `playwright` dependencies in a single multi-stage Dockerfile deployed directly to Render. This ensures target environment packages are identical to local.

---

## Implementation Units

### U1. Supabase Database Schema Setup
- **Goal:** Provision the Postgres schema with RLS and `pgvector` extension enabled.
- **Files:**
  - `src/db/supabase/migrations/20260618000000_init_schema.sql` (NEW)
- **Approach:**
  - Create table mappings for `workspaces`, `workspace_members`, `research_runs`, `graph_nodes`, and `graph_edges`.
  - Add `embedding` column of type `vector(1536)` (or model dimension size) to the `graph_nodes` table.
  - Set up Row-Level Security (RLS) policies verifying `auth.uid()` workspace membership.
- **Test Scenarios:**
  - Verify unauthorized users cannot query workspace research runs.
  - Verify insertion and similarity lookup of vector elements.
- **Verification:** Run migration scripts and check the schema structure on a test Supabase instance.

### U2. Auth Integration in FastAPI & React/Mantine
- **Goal:** Secure the FastAPI API endpoints and integrate login pages in the frontend UI.
- **Files:**
  - `research_engine/auth.py` (NEW)
  - `research_engine/api.py` (MODIFY)
  - `frontend/src/components/Auth/` (NEW)
- **Approach:**
  - Add FastAPI HTTPBearer middleware to validate Supabase JWT tokens.
  - Parse the workspace ID constraint from authenticated JWT claims.
  - Implement Login/Signup and Workspace Select views in Mantine.
- **Test Scenarios:**
  - Send request with missing, expired, or invalid token to FastAPI; verify it returns `401 Unauthorized`.
  - Verify login state persists across page refreshes in UI.
- **Verification:** Manually sign up a test account, log in, and retrieve authenticated endpoints.

### U3. Graphify & pgvector Relational Adaptations
- **Goal:** Re-route graph persistence and BFS/DFS query traversals to the PostgreSQL schema.
- **Files:**
  - `research_engine/knowledge_graph/persistence.py` (NEW/MODIFY)
  - `research_engine/knowledge_graph/query.py` (MODIFY)
- **Approach:**
  - Adapt the Graphify engine to save extracted nodes and relations to the Postgres schema.
  - Write SQL/RPC function querying cosine similarity utilizing the `pgvector` operator (`<=>`).
- **Test Scenarios:**
  - Save a mock knowledge graph; verify entries populate `graph_nodes` and `graph_edges`.
  - Query semantically similar nodes; verify ordering matches vector expectations.
- **Verification:** Run `pytest tests/test_graph_persistence.py` to validate SQL serialization.

### U4. Render Webhook Scraper Worker & Security
- **Goal:** Implement the Python worker endpoint on Render with signature verification.
- **Files:**
  - `research_engine/worker.py` (NEW)
  - `Dockerfile.worker` (NEW)
- **Approach:**
  - Implement a FastAPI listener on the worker container containing HMAC-SHA256 signature validation.
  - Configure the Dockerfile starting from Python 3.11, installing system browser dependencies and run `python -m camoufox fetch`.
- **Test Scenarios:**
  - Send fake payload without correct signature; verify worker returns `403 Forbidden`.
  - Trigger worker with valid signature; verify scraping run executes.
- **Verification:** Deploy to a staging Render environment and run a quick research test run.

### U5. Realtime Event Streaming
- **Goal:** Stream state transitions from the worker to the frontend Client using Supabase Realtime.
- **Files:**
  - `research_engine/worker.py` (MODIFY)
  - `frontend/src/api/realtime.ts` (NEW)
- **Approach:**
  - During research runs, update status fields in the Supabase `research_runs` table from the worker.
  - Subscribe the Mantine UI client to postgres changes via Supabase WebSockets.
- **Test Scenarios:**
  - Start a research run; verify UI updates progress bars in sync with worker state changes.
- **Verification:** Inspect the UI stream updates live during a mock query execution.

---

## Scope Boundaries

### In Scope
- Setup of relational Postgres schemas and indexes.
- Deployment configuration for worker nodes on Render.
- JWT and RLS security implementation.

### Out of Scope
- Support for databases other than Supabase-compliant PostgreSQL.
- Implementing automatic worker container auto-scaling logic.

---

## Risks & Dependencies

- **Database RLS Leakage:** Complex RLS configurations risk exposing data if not thoroughly tested. MITIGATION: Implement unit tests with mock authenticated requests simulating non-workspace access.
- **Cold-start Webhook Delays:** Render web services on free tiers spin down. MITIGATION: Keep the worker active or configure appropriate keep-alive pings to avoid webhook timeouts.
