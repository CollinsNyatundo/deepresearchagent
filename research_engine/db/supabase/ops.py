"""Async Supabase database operations layer.

Wraps the sync Supabase client with asyncio.to_thread() for all operations.
Provides typed CRUD operations for all tables with workspace isolation.

Architecture:
    SupabaseOps (public interface)
    ├── _client: Sync Supabase Client (wrapped in asyncio.to_thread)
    ├── Table operations: workspaces, workspace_members, research_runs,
    │   notes, documents, graph_nodes, graph_edges, citation_verifications,
    │   checkpoints, document_tags
    └── Error handling: SupabaseError, NotFoundError, ValidationError
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol

from research_engine.db.supabase.client import get_supabase_client

logger = logging.getLogger(__name__)


class SupabaseError(Exception):
    """Base error for Supabase operations."""
    pass


class NotFoundError(SupabaseError):
    """Raised when a record is not found."""
    pass


class ValidationError(SupabaseError):
    """Raised when data validation fails."""
    pass


class AuthError(SupabaseError):
    """Raised when authentication/authorization fails."""
    pass


class SupabaseOps:
    """Async operations layer for Supabase database.

    All methods are async and wrap the sync Supabase client
    using asyncio.to_thread() as required by the AGENTS.md rules.
    """

    def __init__(self, client=None):
        self._client = client or get_supabase_client()

    # ─── Internal helpers ────────────────────────────────────────────────

    async def _execute(self, query) -> dict:
        """Execute a Supabase query in a thread pool."""
        try:
            result = await asyncio.to_thread(query.execute)
            return result
        except Exception as e:
            logger.error(f"Supabase query failed: {e}")
            raise SupabaseError(f"Database query failed: {e}") from e

    def _handle_result(self, result: dict, expected_count: int = 1) -> dict | list:
        """Handle Supabase query result, raising errors if needed."""
        data = result.get("data", [])
        if expected_count == 1 and not data:
            raise NotFoundError("Record not found")
        return data[0] if expected_count == 1 else data

    # ─── Workspaces ──────────────────────────────────────────────────────

    async def create_workspace(self, name: str) -> dict:
        """Create a new workspace."""
        result = await self._execute(
            self._client.table("workspaces").insert({"name": name})
        )
        return self._handle_result(result)

    async def get_workspace(self, workspace_id: str) -> dict:
        """Get workspace by ID."""
        result = await self._execute(
            self._client.table("workspaces").select("*").eq("id", workspace_id).single()
        )
        return self._handle_result(result)

    async def list_workspaces_for_user(self, user_id: str) -> list[dict]:
        """List all workspaces a user is a member of."""
        # Get workspace_ids from workspace_members
        member_result = await self._execute(
            self._client.table("workspace_members")
            .select("workspace_id")
            .eq("user_id", user_id)
        )
        workspace_ids = [m["workspace_id"] for m in member_result.get("data", [])]
        if not workspace_ids:
            return []
        # Get workspaces
        result = await self._execute(
            self._client.table("workspaces").select("*").in_("id", workspace_ids)
        )
        return result.get("data", [])

    async def delete_workspace(self, workspace_id: str) -> None:
        """Delete a workspace (cascades to all related data)."""
        await self._execute(
            self._client.table("workspaces").delete().eq("id", workspace_id)
        )

    # ─── Workspace Members ───────────────────────────────────────────────

    async def add_workspace_member(self, workspace_id: str, user_id: str) -> dict:
        """Add a member to a workspace."""
        result = await self._execute(
            self._client.table("workspace_members").insert({
                "workspace_id": workspace_id,
                "user_id": user_id,
            })
        )
        return self._handle_result(result)

    async def verify_workspace_membership(self, workspace_id: str, user_id: str) -> bool:
        """Verify if a user is a member of a workspace."""
        try:
            result = await self._execute(
                self._client.table("workspace_members")
                .select("id")
                .eq("workspace_id", workspace_id)
                .eq("user_id", user_id)
                .limit(1)
            )
            return len(result.get("data", [])) > 0
        except Exception:
            return False

    async def remove_workspace_member(self, workspace_id: str, user_id: str) -> None:
        """Remove a member from a workspace."""
        await self._execute(
            self._client.table("workspace_members")
            .delete()
            .eq("workspace_id", workspace_id)
            .eq("user_id", user_id)
        )

    # ─── Research Runs ───────────────────────────────────────────────────

    async def create_research_run(self, data: dict) -> dict:
        """Create a new research run.

        Required fields: id, workspace_id, user_id, query, status, progress
        """
        result = await self._execute(
            self._client.table("research_runs").insert(data)
        )
        return self._handle_result(result)

    async def get_research_run(self, run_id: str) -> dict:
        """Get research run by ID."""
        result = await self._execute(
            self._client.table("research_runs").select("*").eq("id", run_id).single()
        )
        return self._handle_result(result)

    async def list_research_runs(self, workspace_id: str) -> list[dict]:
        """List all research runs for a workspace."""
        result = await self._execute(
            self._client.table("research_runs")
            .select("*")
            .eq("workspace_id", workspace_id)
            .order("created_at", desc=True)
        )
        return result.get("data", [])

    async def update_research_run(self, run_id: str, data: dict) -> dict:
        """Update a research run."""
        result = await self._execute(
            self._client.table("research_runs").update(data).eq("id", run_id)
        )
        return self._handle_result(result)

    async def delete_research_run(self, run_id: str) -> None:
        """Delete a research run."""
        await self._execute(
            self._client.table("research_runs").delete().eq("id", run_id)
        )

    # ─── Notes ───────────────────────────────────────────────────────────

    async def create_note(self, data: dict) -> dict:
        """Create a new note.

        Required fields: workspace_id, user_id, title, content
        """
        result = await self._execute(
            self._client.table("notes").insert(data)
        )
        return self._handle_result(result)

    async def get_note(self, note_id: str) -> dict:
        """Get note by ID."""
        result = await self._execute(
            self._client.table("notes").select("*").eq("id", note_id).single()
        )
        return self._handle_result(result)

    async def list_notes(self, workspace_id: str) -> list[dict]:
        """List all notes for a workspace."""
        result = await self._execute(
            self._client.table("notes")
            .select("*")
            .eq("workspace_id", workspace_id)
            .order("updated_at", desc=True)
        )
        return result.get("data", [])

    async def update_note(self, note_id: str, data: dict) -> dict:
        """Update a note."""
        result = await self._execute(
            self._client.table("notes").update(data).eq("id", note_id)
        )
        return self._handle_result(result)

    async def delete_note(self, note_id: str) -> None:
        """Delete a note."""
        await self._execute(
            self._client.table("notes").delete().eq("id", note_id)
        )

    async def search_notes(self, workspace_id: str, query: str) -> list[dict]:
        """Search notes using full-text search."""
        # Use tsvector search
        result = await self._execute(
            self._client.table("notes")
            .select("*")
            .eq("workspace_id", workspace_id)
            .text_search("search_vector", query)
        )
        return result.get("data", [])

    # ─── Documents ───────────────────────────────────────────────────────

    async def create_document(self, data: dict) -> dict:
        """Create a new document record."""
        result = await self._execute(
            self._client.table("documents").insert(data)
        )
        return self._handle_result(result)

    async def get_document(self, doc_id: str) -> dict:
        """Get document by ID."""
        result = await self._execute(
            self._client.table("documents").select("*").eq("id", doc_id).single()
        )
        return self._handle_result(result)

    async def list_documents(self, workspace_id: str) -> list[dict]:
        """List all documents for a workspace."""
        result = await self._execute(
            self._client.table("documents")
            .select("*")
            .eq("workspace_id", workspace_id)
            .order("created_at", desc=True)
        )
        return result.get("data", [])

    async def update_document(self, doc_id: str, data: dict) -> dict:
        """Update a document."""
        result = await self._execute(
            self._client.table("documents").update(data).eq("id", doc_id)
        )
        return self._handle_result(result)

    async def delete_document(self, doc_id: str) -> None:
        """Delete a document."""
        await self._execute(
            self._client.table("documents").delete().eq("id", doc_id)
        )

    # ─── Citation Verifications ──────────────────────────────────────────

    async def create_citation_verification(self, data: dict) -> dict:
        """Create a citation verification record."""
        result = await self._execute(
            self._client.table("citation_verifications").insert(data)
        )
        return self._handle_result(result)

    async def list_citation_verifications(self, run_id: str) -> list[dict]:
        """List citation verifications for a run."""
        result = await self._execute(
            self._client.table("citation_verifications")
            .select("*")
            .eq("run_id", run_id)
        )
        return result.get("data", [])

    # ─── Checkpoints ─────────────────────────────────────────────────────

    async def create_checkpoint(self, data: dict) -> dict:
        """Create a checkpoint record."""
        result = await self._execute(
            self._client.table("checkpoints").insert(data)
        )
        return self._handle_result(result)

    async def get_latest_checkpoint(self, run_id: str) -> dict | None:
        """Get latest checkpoint for a run."""
        result = await self._execute(
            self._client.table("checkpoints")
            .select("*")
            .eq("run_id", run_id)
            .order("created_at", desc=True)
            .limit(1)
            .single()
        )
        data = result.get("data")
        if not data:
            return None
        return data[0] if isinstance(data, list) else data

    async def delete_old_checkpoints(self, run_id: str) -> None:
        """Delete all checkpoints for a run (latest-only policy)."""
        await self._execute(
            self._client.table("checkpoints").delete().eq("run_id", run_id)
        )

    # ─── Graph Nodes ─────────────────────────────────────────────────────

    async def create_graph_node(self, data: dict) -> dict:
        """Create a graph node."""
        result = await self._execute(
            self._client.table("graph_nodes").insert(data)
        )
        return self._handle_result(result)

    async def list_graph_nodes(self, run_id: str) -> list[dict]:
        """List graph nodes for a run."""
        result = await self._execute(
            self._client.table("graph_nodes").select("*").eq("run_id", run_id)
        )
        return result.get("data", [])

    async def match_graph_nodes(
        self, query_embedding: list[float], threshold: float, count: int
    ) -> list[dict]:
        """Find similar graph nodes using cosine similarity."""
        result = await self._execute(
            self._client.rpc(
                "match_graph_nodes",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": threshold,
                    "match_count": count,
                }
            )
        )
        return result.get("data", [])

    # ─── Graph Edges ─────────────────────────────────────────────────────

    async def create_graph_edge(self, data: dict) -> dict:
        """Create a graph edge."""
        result = await self._execute(
            self._client.table("graph_edges").insert(data)
        )
        return self._handle_result(result)

    async def list_graph_edges(self, run_id: str) -> list[dict]:
        """List graph edges for a run."""
        result = await self._execute(
            self._client.table("graph_edges").select("*").eq("run_id", run_id)
        )
        return result.get("data", [])

    # ─── Health Check ────────────────────────────────────────────────────

    async def health_check(self) -> dict:
        """Check database connectivity by querying workspaces."""
        try:
            result = await self._execute(
                self._client.table("workspaces").select("count", count="exact").limit(0)
            )
            return {"status": "ok", "connected": True}
        except Exception as e:
            return {"status": "error", "connected": False, "error": str(e)}
