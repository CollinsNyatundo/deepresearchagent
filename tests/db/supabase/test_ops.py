"""TDD tests for Supabase async operations layer.

Tests verify:
1. All operations call correct table methods with correct parameters
2. Workspace isolation is maintained
3. Error handling works correctly
4. Async wrapper uses asyncio.to_thread
5. All tables have corresponding operations
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from research_engine.db.supabase.ops import (
    SupabaseOps,
    SupabaseError,
    NotFoundError,
)


class MockSupabaseQuery:
    """Mock Supabase query builder chain."""

    def __init__(self, table_name: str, return_data=None):
        self.table_name = table_name
        self.return_data = return_data or []
        self._filters = {}
        self._limit = None
        self._order = None
        self._single = False

    def insert(self, data):
        self._insert_data = data
        return self

    def update(self, data):
        self._update_data = data
        return self

    def delete(self):
        self._delete = True
        return self

    def select(self, *cols, **kwargs):
        self._select = cols[0] if cols else "*"
        self._select_kwargs = kwargs
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def in_(self, col, vals):
        self._filters[f"{col}__in"] = vals
        return self

    def limit(self, n):
        self._limit = n
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def single(self):
        self._single = True
        return self

    def text_search(self, col, query):
        self._text_search = (col, query)
        return self

    def execute(self):
        if self._single and not self.return_data:
            # Real Supabase returns a response with error, not an exception
            return {"data": []}
        return {"data": self.return_data}

    def __repr__(self):
        return f"MockQuery({self.table_name})"


class MockSupabaseClient:
    """Mock Supabase client for testing."""

    def __init__(self):
        self._queries = []
        self._next_result = []

    def table(self, name: str):
        query = MockSupabaseQuery(name, self._next_result)
        self._queries.append(query)
        return query

    def rpc(self, func_name: str, params: dict):
        query = MockSupabaseQuery(f"rpc:{func_name}", self._next_result)
        self._queries.append(query)
        return query

    def set_next_result(self, data):
        self._next_result = data

    def get_queries(self):
        return self._queries


@pytest.fixture
def mock_client():
    return MockSupabaseClient()


@pytest.fixture
def ops(mock_client):
    return SupabaseOps(client=mock_client)


# ─── Workspaces Tests ──────────────────────────────────────────────────

class TestWorkspaces:
    """Tests for workspace operations."""

    @pytest.mark.asyncio
    async def test_create_workspace(self, ops, mock_client):
        """Given name, creates workspace."""
        mock_client.set_next_result([{"id": "ws-1", "name": "Test Workspace"}])
        result = await ops.create_workspace("Test Workspace")
        assert result["id"] == "ws-1"
        assert result["name"] == "Test Workspace"
        queries = mock_client.get_queries()
        assert queries[0].table_name == "workspaces"
        assert queries[0]._insert_data == {"name": "Test Workspace"}

    @pytest.mark.asyncio
    async def test_get_workspace(self, ops, mock_client):
        """Given ID, returns workspace."""
        mock_client.set_next_result([{"id": "ws-1", "name": "Test"}])
        result = await ops.get_workspace("ws-1")
        assert result["id"] == "ws-1"
        queries = mock_client.get_queries()
        assert queries[0].table_name == "workspaces"
        assert queries[0]._filters.get("id") == "ws-1"
        assert queries[0]._single is True

    @pytest.mark.asyncio
    async def test_get_workspace_not_found(self, ops, mock_client):
        """Given missing ID, raises NotFoundError."""
        mock_client.set_next_result([])
        with pytest.raises(NotFoundError):
            await ops.get_workspace("missing")

    @pytest.mark.asyncio
    async def test_list_workspaces_for_user(self, ops, mock_client):
        """Given user_id, returns member workspaces."""
        # First query: workspace_members
        # Second query: workspaces
        mock_client.set_next_result([{"workspace_id": "ws-1"}, {"workspace_id": "ws-2"}])
        result = await ops.list_workspaces_for_user("user-1")
        assert len(result) == 2
        queries = mock_client.get_queries()
        assert queries[0].table_name == "workspace_members"
        assert queries[0]._filters.get("user_id") == "user-1"

    @pytest.mark.asyncio
    async def test_list_workspaces_for_user_no_memberships(self, ops, mock_client):
        """Given user with no memberships, returns empty list."""
        mock_client.set_next_result([])
        result = await ops.list_workspaces_for_user("user-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_workspace(self, ops, mock_client):
        """Given ID, deletes workspace."""
        mock_client.set_next_result([{"id": "ws-1"}])
        await ops.delete_workspace("ws-1")
        queries = mock_client.get_queries()
        assert queries[0].table_name == "workspaces"
        assert queries[0]._filters.get("id") == "ws-1"
        assert queries[0]._delete is True


# ─── Workspace Members Tests ───────────────────────────────────────────

class TestWorkspaceMembers:
    """Tests for workspace member operations."""

    @pytest.mark.asyncio
    async def test_add_workspace_member(self, ops, mock_client):
        """Given workspace_id and user_id, adds member."""
        mock_client.set_next_result([{"workspace_id": "ws-1", "user_id": "user-1"}])
        result = await ops.add_workspace_member("ws-1", "user-1")
        assert result["workspace_id"] == "ws-1"
        queries = mock_client.get_queries()
        assert queries[0].table_name == "workspace_members"
        assert queries[0]._insert_data == {"workspace_id": "ws-1", "user_id": "user-1"}

    @pytest.mark.asyncio
    async def test_verify_workspace_membership_true(self, ops, mock_client):
        """Given member user, returns True."""
        mock_client.set_next_result([{"id": "member-1"}])
        result = await ops.verify_workspace_membership("ws-1", "user-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_workspace_membership_false(self, ops, mock_client):
        """Given non-member user, returns False."""
        mock_client.set_next_result([])
        result = await ops.verify_workspace_membership("ws-1", "user-1")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_workspace_member(self, ops, mock_client):
        """Given member, removes them."""
        mock_client.set_next_result([{"id": "member-1"}])
        await ops.remove_workspace_member("ws-1", "user-1")
        queries = mock_client.get_queries()
        assert queries[0].table_name == "workspace_members"
        assert queries[0]._filters.get("workspace_id") == "ws-1"
        assert queries[0]._filters.get("user_id") == "user-1"
        assert queries[0]._delete is True


# ─── Research Runs Tests ───────────────────────────────────────────────

class TestResearchRuns:
    """Tests for research run operations."""

    @pytest.mark.asyncio
    async def test_create_research_run(self, ops, mock_client):
        """Given data, creates research run."""
        data = {
            "id": "run-1", "workspace_id": "ws-1", "user_id": "user-1",
            "query": "AI", "status": "initializing", "progress": 0,
        }
        mock_client.set_next_result([data])
        result = await ops.create_research_run(data)
        assert result["id"] == "run-1"
        queries = mock_client.get_queries()
        assert queries[0].table_name == "research_runs"
        assert queries[0]._insert_data == data

    @pytest.mark.asyncio
    async def test_get_research_run(self, ops, mock_client):
        """Given ID, returns run."""
        mock_client.set_next_result([{"id": "run-1", "query": "AI"}])
        result = await ops.get_research_run("run-1")
        assert result["id"] == "run-1"
        queries = mock_client.get_queries()
        assert queries[0].table_name == "research_runs"
        assert queries[0]._single is True

    @pytest.mark.asyncio
    async def test_list_research_runs(self, ops, mock_client):
        """Given workspace_id, returns runs ordered by created_at desc."""
        mock_client.set_next_result([
            {"id": "run-2", "created_at": "2024-01-02"},
            {"id": "run-1", "created_at": "2024-01-01"},
        ])
        result = await ops.list_research_runs("ws-1")
        assert len(result) == 2
        queries = mock_client.get_queries()
        assert queries[0].table_name == "research_runs"
        assert queries[0]._filters.get("workspace_id") == "ws-1"
        assert queries[0]._order == ("created_at", True)

    @pytest.mark.asyncio
    async def test_update_research_run(self, ops, mock_client):
        """Given ID and data, updates run."""
        update_data = {"status": "complete", "progress": 100}
        mock_client.set_next_result([{"id": "run-1", "status": "complete"}])
        result = await ops.update_research_run("run-1", update_data)
        assert result["status"] == "complete"
        queries = mock_client.get_queries()
        assert queries[0].table_name == "research_runs"
        assert queries[0]._update_data == update_data
        assert queries[0]._filters.get("id") == "run-1"

    @pytest.mark.asyncio
    async def test_delete_research_run(self, ops, mock_client):
        """Given ID, deletes run."""
        mock_client.set_next_result([{"id": "run-1"}])
        await ops.delete_research_run("run-1")
        queries = mock_client.get_queries()
        assert queries[0].table_name == "research_runs"
        assert queries[0]._delete is True


# ─── Notes Tests ───────────────────────────────────────────────────────

class TestNotes:
    """Tests for note operations."""

    @pytest.mark.asyncio
    async def test_create_note(self, ops, mock_client):
        """Given data, creates note."""
        data = {"workspace_id": "ws-1", "user_id": "user-1", "title": "Test", "content": "Body"}
        mock_client.set_next_result([data])
        result = await ops.create_note(data)
        assert result["title"] == "Test"
        queries = mock_client.get_queries()
        assert queries[0].table_name == "notes"

    @pytest.mark.asyncio
    async def test_get_note(self, ops, mock_client):
        """Given ID, returns note."""
        mock_client.set_next_result([{"id": "note-1", "title": "Test"}])
        result = await ops.get_note("note-1")
        assert result["id"] == "note-1"

    @pytest.mark.asyncio
    async def test_list_notes(self, ops, mock_client):
        """Given workspace_id, returns notes ordered by updated_at desc."""
        mock_client.set_next_result([{"id": "note-1"}, {"id": "note-2"}])
        result = await ops.list_notes("ws-1")
        assert len(result) == 2
        queries = mock_client.get_queries()
        assert queries[0].table_name == "notes"
        assert queries[0]._order == ("updated_at", True)

    @pytest.mark.asyncio
    async def test_update_note(self, ops, mock_client):
        """Given ID and data, updates note."""
        mock_client.set_next_result([{"id": "note-1", "title": "Updated"}])
        result = await ops.update_note("note-1", {"title": "Updated"})
        assert result["title"] == "Updated"

    @pytest.mark.asyncio
    async def test_delete_note(self, ops, mock_client):
        """Given ID, deletes note."""
        mock_client.set_next_result([{"id": "note-1"}])
        await ops.delete_note("note-1")
        queries = mock_client.get_queries()
        assert queries[0]._delete is True

    @pytest.mark.asyncio
    async def test_search_notes(self, ops, mock_client):
        """Given workspace_id and query, returns matching notes."""
        mock_client.set_next_result([{"id": "note-1", "title": "AI"}])
        result = await ops.search_notes("ws-1", "AI")
        assert len(result) == 1
        queries = mock_client.get_queries()
        assert queries[0].table_name == "notes"
        assert queries[0]._text_search == ("search_vector", "AI")


# ─── Documents Tests ───────────────────────────────────────────────────

class TestDocuments:
    """Tests for document operations."""

    @pytest.mark.asyncio
    async def test_create_document(self, ops, mock_client):
        """Given data, creates document."""
        data = {"workspace_id": "ws-1", "user_id": "user-1", "filename": "test.pdf"}
        mock_client.set_next_result([data])
        result = await ops.create_document(data)
        assert result["filename"] == "test.pdf"

    @pytest.mark.asyncio
    async def test_list_documents(self, ops, mock_client):
        """Given workspace_id, returns documents."""
        mock_client.set_next_result([{"id": "doc-1"}])
        result = await ops.list_documents("ws-1")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_delete_document(self, ops, mock_client):
        """Given ID, deletes document."""
        mock_client.set_next_result([{"id": "doc-1"}])
        await ops.delete_document("doc-1")
        queries = mock_client.get_queries()
        assert queries[0]._delete is True


# ─── Citation Verifications Tests ────────────────────────────────────

class TestCitationVerifications:
    """Tests for citation verification operations."""

    @pytest.mark.asyncio
    async def test_create_citation_verification(self, ops, mock_client):
        """Given data, creates verification record."""
        data = {"run_id": "run-1", "workspace_id": "ws-1", "citation_text": "Test", "status": "verified"}
        mock_client.set_next_result([data])
        result = await ops.create_citation_verification(data)
        assert result["status"] == "verified"
        queries = mock_client.get_queries()
        assert queries[0].table_name == "citation_verifications"

    @pytest.mark.asyncio
    async def test_list_citation_verifications(self, ops, mock_client):
        """Given run_id, returns verifications."""
        mock_client.set_next_result([{"id": "cv-1"}, {"id": "cv-2"}])
        result = await ops.list_citation_verifications("run-1")
        assert len(result) == 2
        queries = mock_client.get_queries()
        assert queries[0]._filters.get("run_id") == "run-1"


# ─── Checkpoints Tests ─────────────────────────────────────────────────

class TestCheckpoints:
    """Tests for checkpoint operations."""

    @pytest.mark.asyncio
    async def test_create_checkpoint(self, ops, mock_client):
        """Given data, creates checkpoint."""
        data = {"run_id": "run-1", "workspace_id": "ws-1", "phase": "search", "state_json": "{}"}
        mock_client.set_next_result([data])
        result = await ops.create_checkpoint(data)
        assert result["phase"] == "search"

    @pytest.mark.asyncio
    async def test_get_latest_checkpoint(self, ops, mock_client):
        """Given run_id, returns latest checkpoint."""
        mock_client.set_next_result([{"id": "cp-1", "phase": "search"}])
        result = await ops.get_latest_checkpoint("run-1")
        assert result["phase"] == "search"
        queries = mock_client.get_queries()
        assert queries[0].table_name == "checkpoints"
        assert queries[0]._order == ("created_at", True)
        assert queries[0]._limit == 1

    @pytest.mark.asyncio
    async def test_get_latest_checkpoint_none(self, ops, mock_client):
        """Given no checkpoints, returns None."""
        mock_client.set_next_result([])
        result = await ops.get_latest_checkpoint("run-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_old_checkpoints(self, ops, mock_client):
        """Given run_id, deletes all checkpoints."""
        mock_client.set_next_result([{"id": "cp-1"}])
        await ops.delete_old_checkpoints("run-1")
        queries = mock_client.get_queries()
        assert queries[0].table_name == "checkpoints"
        assert queries[0]._delete is True


# ─── Graph Tests ───────────────────────────────────────────────────────

class TestGraphNodes:
    """Tests for graph node operations."""

    @pytest.mark.asyncio
    async def test_create_graph_node(self, ops, mock_client):
        """Given data, creates node."""
        data = {"run_id": "run-1", "id": "node-1", "label": "AI"}
        mock_client.set_next_result([data])
        result = await ops.create_graph_node(data)
        assert result["label"] == "AI"

    @pytest.mark.asyncio
    async def test_list_graph_nodes(self, ops, mock_client):
        """Given run_id, returns nodes."""
        mock_client.set_next_result([{"id": "node-1"}])
        result = await ops.list_graph_nodes("run-1")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_match_graph_nodes(self, ops, mock_client):
        """Given embedding, returns similar nodes."""
        mock_client.set_next_result([{"id": "node-1", "similarity": 0.95}])
        result = await ops.match_graph_nodes([0.1] * 1536, 0.8, 5)
        assert len(result) == 1
        queries = mock_client.get_queries()
        assert queries[0].table_name == "rpc:match_graph_nodes"


class TestGraphEdges:
    """Tests for graph edge operations."""

    @pytest.mark.asyncio
    async def test_create_graph_edge(self, ops, mock_client):
        """Given data, creates edge."""
        data = {"run_id": "run-1", "source": "node-1", "target": "node-2"}
        mock_client.set_next_result([data])
        result = await ops.create_graph_edge(data)
        assert result["source"] == "node-1"

    @pytest.mark.asyncio
    async def test_list_graph_edges(self, ops, mock_client):
        """Given run_id, returns edges."""
        mock_client.set_next_result([{"id": "edge-1"}])
        result = await ops.list_graph_edges("run-1")
        assert len(result) == 1


# ─── Health Check Tests ────────────────────────────────────────────────

class TestHealthCheck:
    """Tests for database health check."""

    @pytest.mark.asyncio
    async def test_health_check_ok(self, ops, mock_client):
        """Given healthy DB, returns ok."""
        mock_client.set_next_result([{"count": 0}])
        result = await ops.health_check()
        assert result["status"] == "ok"
        assert result["connected"] is True

    @pytest.mark.asyncio
    async def test_health_check_error(self, ops, mock_client):
        """Given failing DB, returns error."""
        # Make execute fail
        with patch.object(ops, "_execute", side_effect=Exception("Connection refused")):
            result = await ops.health_check()
            assert result["status"] == "error"
            assert result["connected"] is False


# ─── Error Handling Tests ──────────────────────────────────────────────

class TestErrorHandling:
    """Tests for error handling across all operations."""

    @pytest.mark.asyncio
    async def test_supabase_error_raised(self, ops, mock_client):
        """Given DB error, raises SupabaseError."""
        with patch("research_engine.db.supabase.ops.asyncio.to_thread", side_effect=Exception("DB down")):
            with pytest.raises(SupabaseError, match="Database query failed"):
                await ops.get_workspace("ws-1")

    @pytest.mark.asyncio
    async def test_not_found_error(self, ops, mock_client):
        """Given missing record, raises NotFoundError."""
        mock_client.set_next_result([])
        with pytest.raises(NotFoundError):
            await ops.get_workspace("missing")
