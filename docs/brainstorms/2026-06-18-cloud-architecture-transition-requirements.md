---
topic: cloud-architecture-transition
date: 2026-06-18
title: Cloud Architecture Transition Requirements for Deep Research Agent
---

# Cloud Architecture Transition Requirements

## Summary

This document defines the requirements for transitioning the local-first Deep Research Agent (DRE) to a collaborative, cloud-supported SaaS architecture. The system split utilizes Supabase for database, authentication, and vector search (`pgvector`), combined with Render for long-running headless browser workers.

---

## Problem Frame

The current Deep Research Agent operates exclusively as a local-first developer tool. While this provides excellent privacy and avoids server-side browser execution costs, it creates three primary pain points:
1. Research runs cannot be easily shared or collaborated on across teams.
2. Background research cycles are tied to the user's local machine resources, forcing them to keep their computer running and preventing asynchronous mobile or web monitoring.
3. Persistent caching, graph modularity metrics, and telemetry data are isolated per developer, preventing collaborative enrichment of the shared knowledge graph.

---

## Key Decisions

- **Split BaaS + PaaS Architecture:** The control plane (auth, graph sync, metadata) resides on a managed BaaS (Supabase) to minimize backend plumbing, while execution compute (scraping workers) runs on a PaaS container service (Render) to accommodate heavy headless browser runtimes.
- **Unified Relational Vector Storage (Supabase `pgvector`):** The Graphify knowledge graph nodes, relations, and embeddings are stored inside a single transactional PostgreSQL instance. Relational queries and semantic searches are executed via SQL JOINs in a single database roundtrip, rejecting the multi-engine complexity of Appwrite + Qdrant.
- **Docker-Based Scrapers (Render Workers):** Headless Camoufox/Playwright browsers are packaged into a Python container running on Render, avoiding serverless timeout constraints during long-running research loops (up to 15 minutes).
- **Self-Hosting Trade-off:** Acknowledge that local-first developers who wish to self-host the cloud-supported version will face higher setup complexity due to Supabase's multi-container orchestration stack compared to lightweight alternatives.

---

## Requirements

### User Authentication & Collaboration
- R1. The system must support email/password and OAuth authentication using Supabase Auth.
- R2. The system must partition all research runs, reports, and knowledge graphs under a Workspace model, allowing multiple users to view and share data within the same workspace.
- R3. The system must enforce Row-Level Security (RLS) policies on all tables so that users can only access graphs and reports belonging to their active workspace.

### Graph & Vector Storage
- R4. The database must store the Graphify knowledge graph entities and edges in relational Postgres tables.
- R5. The database must store semantic embeddings for knowledge graph nodes using `pgvector` columns.
- R6. The backend must provide a unified SQL interface to query semantically similar nodes and their adjacent relations within a single database request.

### Background Worker Execution
- R7. The system must orchestrate background research tasks using Supabase Database Webhooks as the primary stateless event trigger, with a fallback option for an external message queue if task queuing or rate-limiting guarantees are required.
- R8. The worker must run as a persistent container on Render, configured with Playwright and the Camoufox browser binary.
- R9. The worker must stream real-time research state transitions (e.g., planning, scraping, reflecting) back to the Supabase database, which broadcasts them to the frontend via Supabase Realtime.
- R10. The Render worker endpoint must validate a secure signature or shared token for all incoming webhook requests to prevent unauthorized research execution.

---

## Scope Boundaries

### In Scope
- Migration of local schemas to Supabase Postgres database structure.
- Dockerfile configuration for deploying the FastAPI backend and scrapers on Render.
- Supabase Auth middleware integration in the Mantine frontend and FastAPI backend.

### Outside this product's identity
- Native mobile applications (DRE remains a web-based developer workspace).
- Complex stripe billing tiers (restricted to basic workspace access levels for the initial transition).

---

## Dependencies / Assumptions

- **OpenRouter Gateway:** The cloud deployment assumes continued access to LLM reasoning models via the OpenRouter API gateway.
- **Camoufox Binary Size:** The Render worker environment assumes sufficient disk space and memory allocation to pre-package and build the Camoufox Firefox browser engine.
- **pgvector Index Memory:** The database tier assumes sufficient shared buffers memory to index node embeddings via HNSW.
