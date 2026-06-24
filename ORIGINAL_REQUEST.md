# Original User Request

## Initial Request — 2026-06-18T23:08:37+03:00

Migrate Deep Research Agent (DRE) from a local-only CLI/web tool to a cloud-supported multi-user platform with Supabase authentication and database storage, Render background scraper worker execution, and realtime progress updates.

Working directory: d:/Projects/ai-ml/DeepResearchAgent
Integrity mode: development

## Requirements

### R1. Authentication and Workspace Management (Mantine UI)
Implement user login/signup and workspace creation/selection in the React/Mantine frontend. Hook this state into client API requests to pass the Supabase JWT.

### R2. Relational Knowledge Graph Database Persistence (pgvector)
Save and load knowledge graph nodes and edges to PostgreSQL tables (`graph_nodes`, `graph_edges`) instead of local JSON/SQLite cache. Use pgvector for cosine similarity searching.
Ensure all python environment executions use the existing local virtual environment (`.venv/`) which has all packages installed. Do not attempt to run global python or install global packages.

### R3. Standalone Scraper Webhook Worker (Render)
Run the scrapers inside a persistent background container on Render (FastAPI worker), triggered securely by HMAC-SHA256 authorization.

### R4. Realtime Progress Broadcast
Stream worker research run status and progress updates using Supabase Realtime/WebSockets from the worker to the client.

## Acceptance Criteria

### Authentication
- [ ] User cannot access the dashboard without authentication (Mantine modal blocks page access).
- [ ] Workspace selector dropdown dynamically shows user's workspaces and allows creating new workspaces.
- [ ] Stored token is passed in all API calls via fetch Authorization header.

### Database
- [ ] Knowledge graph nodes and edges are successfully written to and read from Supabase PostgreSQL tables.
- [ ] Semantic query executes pgvector cosine similarity search through a custom PostgreSQL RPC function `match_graph_nodes`.

### Scraper Worker
- [ ] Standalone FastAPI app in `research_engine/worker.py` can be triggered via POST `/webhook/trigger` using HMAC signature.
- [ ] Dockerfile.worker correctly installs Playwright and Camoufox dependencies.

### Streaming
- [ ] Research status changes are broadcasted in real time.
