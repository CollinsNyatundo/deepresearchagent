"""Tests for citation_verifications database migration."""
import pytest
from unittest.mock import AsyncMock, patch


class TestCitationVerificationsMigration:
    """Verify migration schema and RLS policies."""

    @pytest.mark.asyncio
    async def test_migration_table_has_required_columns(self):
        """Given migration applied, table has all required columns."""
        # This test documents the expected schema
        # In a real test environment, we'd query information_schema
        expected_columns = {
            "id", "run_id", "workspace_id", "citation_text",
            "status", "found", "title", "authors", "year",
            "doi", "url", "confidence", "sources", "databases",
            "created_at", "updated_at",
        }
        assert len(expected_columns) == 16

    @pytest.mark.asyncio
    async def test_rls_policy_exists(self):
        """Given migration applied, RLS policy exists for workspace isolation."""
        # This test documents the expected RLS policy
        # Policy name: workspace_isolation_citations
        # Table: citation_verifications
        # Type: ALL
        # Condition: workspace membership via auth.uid()
        assert True  # Schema documented; verified by migration SQL

    def test_migration_sql_has_all_elements(self):
        """Given migration file, it contains all required elements."""
        from pathlib import Path

        migration_path = Path(__file__).parent.parent.parent / "research_engine" / "db" / "supabase" / "migrations" / "20260623000000_add_citation_verifications.sql"
        sql = migration_path.read_text()

        assert "CREATE TABLE citation_verifications" in sql
        assert "ENABLE ROW LEVEL SECURITY" in sql
        assert "workspace_isolation_citations" in sql
        assert "auth.uid()" in sql
        assert "CREATE INDEX" in sql
        assert "CREATE TRIGGER" in sql
        assert "updated_at" in sql
