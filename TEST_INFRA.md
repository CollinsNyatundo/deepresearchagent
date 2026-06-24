# E2E Test Infrastructure & Test Case Specification

## 1. Test Infrastructure Overview

This document specifies the requirement-driven, opaque-box E2E testing infrastructure and methodologies for the Deep Research Agent (DRE) platform. E2E tests run externally against the FastAPI endpoints, Supabase database storage layer, and background scraper workers using the local virtual environment `.venv/`.

### Directory Structure
```
tests/e2e/
├── __init__.py           # E2E testing package initializer
├── conftest.py           # Fixtures for configuration, mock tokens, HMAC signing, and client wrappers
└── test_environment.py   # Smoke test to verify local virtual environment imports and fixture mechanics
```

### Core Testing Fixtures (in `conftest.py`)
- **`generate_mock_jwt`**: Programmatically generates a Supabase HS256-signed JWT token signed with `SUPABASE_JWT_SECRET` (defaulting to `"super-secret-supabase-jwt-key-placeholder"`). Allows overriding claims (`sub`, `email`, `role`, `aud`, `exp`).
- **`mock_auth_headers`**: Provides default `Authorization: Bearer <mock_jwt>` headers.
- **`generate_webhook_signature`**: Generates a valid HMAC-SHA256 signature for webhook requests using a shared secret (`WEBHOOK_HMAC_SECRET`).
- **`e2e_test_client`**: A pre-configured synchronous `fastapi.testclient.TestClient` that defaults to using `mock_auth_headers`.
- **`e2e_async_client`**: A pre-configured `httpx.AsyncClient` for async test cases.
- **`sse_event_parser`**: Utility to parse SSE event streams (`data: {...}\n\n`) into structured JSON payload objects.

---

## 2. Test Selection & Combinatorics Methodologies

Our E2E test plan applies rigorous black-box testing methodologies to ensure high coverage and reliability:

### A. Category-Partitioning
We divide inputs and environmental states into distinct, mutually exclusive partitions:
1. **Authentication Token Status**: [Valid, Invalid Signature, Expired, Missing Header, Wrong Audience, Malformed Token].
2. **Workspace Association**: [Associated with active user, Not associated with active user, Non-existent workspace, Empty workspace list].
3. **Graph Similarity Inputs**: [Highly matching text/embedding, Zero matching text, Negative threshold, Null query].
4. **Webhook signature status**: [Valid HMAC, Invalid HMAC, Missing X-Webhook-Signature header, Expired timestamp signature].
5. **SSE Progress Stream State**: [Connected, Interrupted mid-stream, Empty stream, Stream completed with marker].

### B. Boundary Value Analysis (BVA)
We identify boundary conditions for quantitative parameters:
1. **JWT Expiration**: Exactly 0 seconds remaining, 1 second remaining, -1 second (expired).
2. **Similarity Threshold**: exactly `-1.0` (minimum cosine similarity), `0.0` (orthogonal), `1.0` (perfect match), and boundary violations like `1.01` or `-1.01`.
3. **Research Depth**: Min depth (`1`), max depth (`5`), and invalid depths (`0`, `6`).
4. **Workspace Name Size**: Empty string (`0` characters), exactly `1` character, exactly `255` characters, and boundary violations (`256+` characters).
5. **Scraper request size**: Empty body (`0` bytes), max body size.

### C. Pairwise Combinatorial Testing
We test combinations of discrete options using pairwise arrays:
- **Combination Factor 1**: Authentication method (JWT Bearer Token / Anonymous / Invalid Token).
- **Combination Factor 2**: Workspace membership role (Workspace Owner / Workspace Member / Non-member / Revoked).
- **Combination Factor 3**: API request type (Graph Query / Research Execution / Stream Subscription).
This ensures coverage of interaction bugs between Auth state and API actions without needing to run $3 \times 4 \times 3 = 36$ tests (reduced to 12 pairwise combinations).

### D. Workload / E2E Campaign Scenarios
Simulates realistic, multi-step user paths:
- **Campaign 1 (Standard Happy Path)**: Authenticate User -> Create Workspace -> Trigger webhook with valid HMAC -> Stream research progress via SSE -> Verify knowledge graph written to DB -> Query semantic similarity on pgvector.

---

## 3. Feature-Specific Test Case Specifications

### F1: Authentication and Workspace Management (R1)
- **happy-path (Tier 1)**:
  - `test_auth_success`: Valid Bearer JWT returns dashboard content / status 200.
  - `test_workspace_create`: Create a new workspace with valid name.
  - `test_workspace_select`: Select workspace and retrieve runs filtered by `workspace_id`.
  - `test_workspace_members_list`: Retrieve member list for workspace.
  - `test_jwt_signature_check`: Successful access using dynamically generated valid JWT.
- **boundary & corner (Tier 2)**:
  - `test_auth_expired_jwt`: Token past `exp` claim returns HTTP 401.
  - `test_auth_invalid_signature`: Token signed with different key returns HTTP 401.
  - `test_auth_missing_header`: Request without Authorization header returns HTTP 401.
  - `test_workspace_create_empty_name`: Creating workspace with empty name returns HTTP 400.
  - `test_workspace_access_denied`: Accessing workspace that user does not belong to returns HTTP 403.

### F2: Relational Knowledge Graph Persistence and Similarity Query (R2)
- **happy-path (Tier 1)**:
  - `test_graph_write_nodes_edges`: Persists node and edge models to `graph_nodes` and `graph_edges` tables.
  - `test_graph_read_nodes_edges`: Loads correct node/edge structure by `run_id`.
  - `test_similarity_rpc_exact_match`: RPC `match_graph_nodes` finds exact query embedding with similarity ~1.0.
  - `test_similarity_rpc_under_threshold`: Query returns no results if threshold is set to 1.0 (strict).
  - `test_similarity_rpc_default_limit`: Respects max results limit when finding matching nodes.
- **boundary & corner (Tier 2)**:
  - `test_similarity_invalid_threshold`: Similarity threshold < -1.0 or > 1.0 returns HTTP 400.
  - `test_graph_write_isolated_nodes`: Persists nodes with no edges without failing integrity.
  - `test_graph_read_nonexistent_run`: Reading knowledge graph for missing run returns HTTP 404.
  - `test_similarity_empty_query_embedding`: Passing empty or null embedding vector returns HTTP 400.
  - `test_similarity_rpc_negative_threshold`: Cosine similarity search with negative threshold (-1.0) returns all nodes.

### F3: Standalone Scraper Worker execution & HMAC Security (R3)
- **happy-path (Tier 1)**:
  - `test_webhook_trigger_authorized`: POST `/webhook/trigger` with valid HMAC signature starts scraping job.
  - `test_webhook_response_format`: Trigger returns task ID and confirmation structure.
  - `test_webhook_trigger_uses_camoufox`: Dynamic fetcher falls back to stealthy camoufox for scraping execution.
  - `test_webhook_trigger_uses_playwright`: Dynamic fetcher handles JS rendering if needed.
  - `test_webhook_custom_secret`: Custom HMAC secret overrides default and authenticates correctly.
- **boundary & corner (Tier 2)**:
  - `test_webhook_trigger_unauthorized`: Trigger with incorrect HMAC signature returns HTTP 403.
  - `test_webhook_trigger_missing_signature`: Trigger without `X-Webhook-Signature` header returns HTTP 400 or 403.
  - `test_webhook_trigger_empty_body`: Empty POST request body returns HTTP 400.
  - `test_webhook_trigger_expired_timestamp`: If timestamp/signature verification checks ages, reject signatures older than limit.
  - `test_webhook_trigger_invalid_json`: Malformed JSON webhook payload returns HTTP 400.

### F4: Realtime progress streaming (R4)
- **happy-path (Tier 1)**:
  - `test_sse_stream_connection`: POST `/research/stream` establishes SSE stream (content-type `text/event-stream`).
  - `test_sse_progress_increments`: SSE events contain ascending progress values (`0` to `100`).
  - `test_sse_research_steps`: Stream emits detail packets containing research steps (searching, scraping, synthesizing).
  - `test_supabase_realtime_broadcast`: Broadcasts progress updates via Supabase Realtime channel.
  - `test_sse_complete_marker`: Emits end-of-stream complete event indicating research summary.
- **boundary & corner (Tier 2)**:
  - `test_sse_stream_auth_failure`: Unauthenticated SSE requests are rejected (HTTP 401).
  - `test_sse_client_disconnect`: Server terminates research thread cleanly if client disconnects mid-stream.
  - `test_sse_step_limit_boundary`: Depth 1 results in fewer cycles/events, respecting boundary limit.
  - `test_sse_error_propagation`: If LLM or Scraper fails, error payload is streamed through SSE before closure.
  - `test_realtime_progress_throttle`: High-frequency updates are throttled to prevent client UI freeze.

---

## 4. How to Execute E2E Tests

Ensure you have configured the necessary test environment variables or default values in your local `.env` file:
```env
SUPABASE_JWT_SECRET=super-secret-supabase-jwt-key-placeholder
WEBHOOK_HMAC_SECRET=test-webhook-hmac-shared-secret-key
```

Run tests using the local virtual environment `.venv`:
```bash
# Execute only the E2E test suite
.\.venv\Scripts\pytest tests/e2e/ -v

# Execute only environment verify tests
.\.venv\Scripts\pytest tests/e2e/test_environment.py -v
```
