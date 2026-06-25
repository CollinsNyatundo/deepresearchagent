---
title: "fix: Resolve 500 errors on /notes, /documents, and /runs endpoints"
type: fix
status: active
date: 2026-06-25
---

# fix: Resolve 500 errors on /notes, /documents, and /runs endpoints

## Problem Frame

The backend returns HTTP 500 errors in the Notes module (GET /notes), Documents module
(GET /documents), and Research module (GET /runs). Login works correctly (Supabase JWT
auth is intact), but all workspace-scoped data endpoints fail after authentication.

Root-cause analysis identified four distinct bugs:

### Bug 1 — verify_workspace_membership return value is ignored

In GET /notes (L1698) and GET /documents (L2091) the call is:
    await verify_workspace_membership(client, workspace_id, user_id)
The boolean return is never checked. If the downstream Supabase query fails due to RLS,
an unhandled exception is raised -> 500.

### Bug 2 — RLS blocks backend queries when SUPABASE_KEY is the anon key (THE ACTUAL CAUSE)

The backend Supabase client uses the anon key or a key without the authenticated
user's session. Supabase RLS on workspace_members, notes, and documents tables uses
auth.uid() to restrict rows. When the backend queries these tables using the anon key,
auth.uid() returns NULL -> RLS blocks all rows -> empty arrays or PGRST301 errors -> 500.

Fix: Set SUPABASE_KEY to the service-role key (bypasses RLS). The backend already
validates JWT auth independently, so this is the correct and safe approach.

### Bug 3 — documents table insert sends tags column that does not exist

In POST /documents/upload (L2066), the insert sends "tags": tag_list.
The documents table has NO tags column. Tags are in the document_tags junction table.
This causes PostgreSQL column-not-found error -> 500 on every upload.

### Bug 4 — Raw Supabase error strings exposed in 500 responses

All exception handlers do raise HTTPException(status_code=500, detail=str(e)),
which leaks internal Supabase/PostgreSQL error details to clients.

## Proposed Changes

### research_engine/db/supabase/client.py
- Add a startup warning when SUPABASE_KEY appears to be an anon key (JWT decode check)

### research_engine/api.py

U1: Change verify_workspace_membership to raise HTTPException(403) directly
    instead of returning False - eliminates all 30+ call-site boolean check redundancies
    and the silent proceed-on-False bug in notes/docs endpoints.

U2: Fix GET /notes (L1698) - already handled by U1

U3: Fix GET /documents (L2091) - already handled by U1

U4: Fix POST /documents/upload (L2057-2069)
    - Remove "tags": tag_list from documents insert
    - After getting the inserted document id, insert rows into document_tags table

U5: Sanitize 500 error detail strings to not expose raw Supabase errors
    - For notes/docs/runs catch blocks: return generic message + log full error

U6: Extend _lifespan startup to test Supabase connectivity and log actionable warning

## Verification Plan

### Automated
- py -m py_compile research_engine/api.py

### Manual
1. Restart backend: research serve
2. Notes page loads without 500 error
3. Documents page loads without 500 error
4. Research runs list loads without 500 error
5. Document upload with tags succeeds and document_tags table has rows

## Key Technical Decision

Use service-role key for all backend Supabase queries. The backend validates JWT
auth independently via verify_supabase_jwt, so server-side queries should not be
limited by anon-key RLS restrictions. The service-role key must never be sent to the
frontend.

