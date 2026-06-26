"""Exhaustive tests for checkpoint manager with serialization, validation, and resume.
"""
import pytest
from unittest.mock import AsyncMock

from research_engine.checkpoints.manager import (
    CheckpointManager,
    CheckpointTooLargeError,
    CheckpointNotFoundError,
    StateValidationError,
    ResearchState,
    StateSerializer,
    StateValidator,
    ResumeOrchestrator,
    CURRENT_SCHEMA_VERSION,
)


class TestStateSerializer:
    """Tests for state serialization with compression."""

    def test_serialize_deserialize_roundtrip(self):
        """Given state, serialization round-trips correctly."""
        serializer = StateSerializer()
        state = ResearchState(
            run_id="run-123",
            phase="search",
            sources=[{"url": "https://example.com", "title": "Test"}],
            partial_report="Partial...",
            metadata={"model": "deepseek"},
        )

        serialized = serializer.serialize(state)
        restored = serializer.deserialize(serialized)

        assert restored.run_id == state.run_id
        assert restored.phase == state.phase
        assert restored.partial_report == state.partial_report
        assert restored.metadata == state.metadata
        assert restored.sources == state.sources

    def test_serialize_compresses_data(self):
        """Given state, serialized data is compressed."""
        serializer = StateSerializer()
        state = ResearchState(
            run_id="run-123",
            phase="search",
            sources=[{"content": "x" * 10000}],
        )

        serialized = serializer.serialize(state)
        # Compressed should be smaller than raw JSON
        import json
        raw_size = len(json.dumps(state.to_dict()).encode())
        assert len(serialized) < raw_size

    def test_serialize_truncates_long_source_content(self):
        """Given long source content, serializer truncates it."""
        serializer = StateSerializer()
        long_content = "x" * 5000
        state = ResearchState(
            run_id="run-123",
            phase="search",
            sources=[{"content": long_content}],
        )

        serialized = serializer.serialize(state)
        restored = serializer.deserialize(serialized)
        assert "... [truncated]" in restored.sources[0]["content"]

    def test_size_returns_uncompressed_size(self):
        """Given serialized data, size returns uncompressed length."""
        serializer = StateSerializer()
        state = ResearchState(run_id="run-123", phase="search")
        serialized = serializer.serialize(state)
        size = serializer.size(serialized)
        assert size > 0
        assert size > len(serialized)  # Uncompressed > compressed


class TestStateValidator:
    """Tests for state validation."""

    def test_validate_valid_state(self):
        """Given valid state, returns no errors."""
        validator = StateValidator()
        state = ResearchState(run_id="run-123", phase="search")
        errors = validator.validate(state)
        assert errors == []

    def test_validate_missing_run_id(self):
        """Given missing run_id, returns error."""
        validator = StateValidator()
        state = ResearchState(run_id="", phase="search")
        errors = validator.validate(state)
        assert any("run_id" in e for e in errors)

    def test_validate_invalid_phase(self):
        """Given invalid phase, returns error."""
        validator = StateValidator()
        state = ResearchState(run_id="run-123", phase="invalid_phase")
        errors = validator.validate(state)
        assert any("Invalid phase" in e for e in errors)

    def test_validate_all_valid_phases(self):
        """Given all valid phases, no errors."""
        validator = StateValidator()
        valid_phases = validator.VALID_PHASES
        for phase in valid_phases:
            state = ResearchState(run_id="run-123", phase=phase)
            errors = validator.validate(state)
            assert errors == [], f"Phase {phase} failed validation: {errors}"

    def test_validate_newer_schema_version(self):
        """Given newer schema version, returns error."""
        validator = StateValidator()
        state = ResearchState(
            run_id="run-123",
            phase="search",
            schema_version=CURRENT_SCHEMA_VERSION + 1,
        )
        errors = validator.validate(state)
        assert any("newer" in e.lower() for e in errors)

    def test_validate_non_serializable_sources(self):
        """Given non-serializable sources, returns error."""
        validator = StateValidator()
        state = ResearchState(
            run_id="run-123",
            phase="search",
            sources=[{"object": object()}],  # Not JSON serializable
        )
        errors = validator.validate(state)
        assert any("serializable" in e.lower() for e in errors)

    def test_is_compatible_true(self):
        """Given valid state, is_compatible is True."""
        validator = StateValidator()
        state = ResearchState(run_id="run-123", phase="search")
        assert validator.is_compatible(state) is True

    def test_is_compatible_false(self):
        """Given invalid state, is_compatible is False."""
        validator = StateValidator()
        state = ResearchState(run_id="", phase="invalid")
        assert validator.is_compatible(state) is False


class TestCheckpointManager:
    """Tests for checkpoint manager with full features."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_save_validates_state(self, mock_db):
        """Given invalid state, save raises validation error."""
        manager = CheckpointManager(db_client=mock_db)
        state = ResearchState(run_id="", phase="invalid")
        with pytest.raises(StateValidationError):
            await manager.save("run-123", "search", state)

    @pytest.mark.asyncio
    async def test_save_serializes_and_compresses(self, mock_db):
        """Given state, save serializes and compresses."""
        manager = CheckpointManager(db_client=mock_db)
        state = ResearchState(run_id="run-123", phase="search")

        mock_db.insert_checkpoint.return_value = {"id": "cp-1"}

        result = await manager.save("run-123", "search", state)
        assert result["id"] == "cp-1"

        # Verify insert was called with compressed data
        call_kwargs = mock_db.insert_checkpoint.call_args[1]
        assert "state_data" in call_kwargs
        assert isinstance(call_kwargs["state_data"], bytes)

    @pytest.mark.asyncio
    async def test_save_deletes_previous(self, mock_db):
        """Given new checkpoint, old one is deleted."""
        manager = CheckpointManager(db_client=mock_db)
        run_id = "run-123"

        await manager.save(run_id, "search", ResearchState(run_id=run_id, phase="search"))
        await manager.save(run_id, "synthesize", ResearchState(run_id=run_id, phase="synthesize"))

        assert mock_db.delete_old_checkpoints.call_count == 2

    @pytest.mark.asyncio
    async def test_save_enforces_size_limit(self, mock_db):
        """Given oversized state, raises CheckpointTooLargeError."""
        manager = CheckpointManager(db_client=mock_db, max_size_bytes=100)
        state = ResearchState(
            run_id="run-123",
            phase="search",
            sources=[{"content": "x" * 500}],
        )
        with pytest.raises(CheckpointTooLargeError):
            await manager.save("run-123", "search", state)

    @pytest.mark.asyncio
    async def test_load_latest_deserializes_compressed(self, mock_db):
        """Given compressed checkpoint, load_latest decompresses."""
        serializer = StateSerializer()
        state = ResearchState(run_id="run-123", phase="synthesize")
        compressed = serializer.serialize(state)

        mock_db.get_latest_checkpoint.return_value = {
            "phase": "synthesize",
            "state_data": compressed,
        }

        manager = CheckpointManager(db_client=mock_db)
        result = await manager.load_latest("run-123")

        assert result.phase == "synthesize"
        assert result.run_id == "run-123"

    @pytest.mark.asyncio
    async def test_load_latest_validates_state(self, mock_db):
        """Given invalid checkpoint, load_latest raises validation error."""
        serializer = StateSerializer()
        state = ResearchState(run_id="", phase="invalid")  # Invalid
        compressed = serializer.serialize(state)

        mock_db.get_latest_checkpoint.return_value = {
            "phase": "invalid",
            "state_data": compressed,
        }

        manager = CheckpointManager(db_client=mock_db)
        with pytest.raises(StateValidationError):
            await manager.load_latest("run-123")

    @pytest.mark.asyncio
    async def test_resume_raises_when_no_checkpoint(self, mock_db):
        """Given no checkpoint, resume raises CheckpointNotFoundError."""
        mock_db.get_latest_checkpoint.return_value = None
        manager = CheckpointManager(db_client=mock_db)
        with pytest.raises(CheckpointNotFoundError):
            await manager.resume("nonexistent")

    @pytest.mark.asyncio
    async def test_cleanup_old_deletes_before_cutoff(self, mock_db):
        """Given old checkpoints, cleanup deletes them."""
        mock_db.delete_checkpoints_before.return_value = 5
        manager = CheckpointManager(db_client=mock_db)
        deleted = await manager.cleanup_old(days=7)
        assert deleted == 5

    @pytest.mark.asyncio
    async def test_list_checkpoints(self, mock_db):
        """Given run_id, list_checkpoints returns all."""
        mock_db.get_checkpoints.return_value = [
            {"phase": "search"},
            {"phase": "synthesize"},
        ]
        manager = CheckpointManager(db_client=mock_db)
        result = await manager.list_checkpoints("run-123")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_stats(self, mock_db):
        """Given stats call, returns storage statistics."""
        mock_db.get_checkpoint_stats.return_value = {"total": 10, "total_size": 50000}
        manager = CheckpointManager(db_client=mock_db)
        stats = await manager.get_stats()
        assert stats["total"] == 10

    @pytest.mark.asyncio
    async def test_no_db_returns_metadata(self):
        """Given no DB client, save returns metadata."""
        manager = CheckpointManager(db_client=None)
        state = ResearchState(run_id="run-123", phase="search")
        result = await manager.save("run-123", "search", state)
        assert result["run_id"] == "run-123"
        assert result["compressed"] is True

    @pytest.mark.asyncio
    async def test_no_db_load_returns_none(self):
        """Given no DB client, load_latest returns None."""
        manager = CheckpointManager(db_client=None)
        result = await manager.load_latest("run-123")
        assert result is None


class TestResumeOrchestrator:
    """Tests for resume orchestrator."""

    @pytest.mark.asyncio
    async def test_can_resume_true(self):
        """Given checkpoint exists, can_resume is True."""
        mock_db = AsyncMock()
        serializer = StateSerializer()
        state = ResearchState(run_id="run-123", phase="search")
        mock_db.get_latest_checkpoint.return_value = {
            "state_data": serializer.serialize(state),
        }
        cm = CheckpointManager(db_client=mock_db)
        orchestrator = ResumeOrchestrator(cm)
        assert await orchestrator.can_resume("run-123") is True

    @pytest.mark.asyncio
    async def test_can_resume_false(self):
        """Given no checkpoint, can_resume is False."""
        mock_db = AsyncMock()
        mock_db.get_latest_checkpoint.return_value = None
        cm = CheckpointManager(db_client=mock_db)
        orchestrator = ResumeOrchestrator(cm)
        assert await orchestrator.can_resume("nonexistent") is False

    @pytest.mark.asyncio
    async def test_resume_returns_state_and_phase(self):
        """Given checkpoint, resume returns state and next phase."""
        mock_db = AsyncMock()
        serializer = StateSerializer()
        state = ResearchState(run_id="run-123", phase="search")
        mock_db.get_latest_checkpoint.return_value = {
            "state_data": serializer.serialize(state),
        }
        cm = CheckpointManager(db_client=mock_db)
        orchestrator = ResumeOrchestrator(cm)
        result_state, next_phase = await orchestrator.resume("run-123")
        assert result_state.phase == "search"
        assert next_phase == "search"  # Re-run current phase

    @pytest.mark.asyncio
    async def test_resume_complete_phase(self):
        """Given complete phase, resume returns complete."""
        mock_db = AsyncMock()
        serializer = StateSerializer()
        state = ResearchState(run_id="run-123", phase="complete")
        mock_db.get_latest_checkpoint.return_value = {
            "state_data": serializer.serialize(state),
        }
        cm = CheckpointManager(db_client=mock_db)
        orchestrator = ResumeOrchestrator(cm)
        result_state, next_phase = await orchestrator.resume("run-123")
        assert next_phase == "complete"

    def test_get_progress(self):
        """Given state, get_progress returns percentage."""
        mock_db = AsyncMock()
        cm = CheckpointManager(db_client=mock_db)
        orchestrator = ResumeOrchestrator(cm)
        state = ResearchState(
            run_id="run-123",
            phase="synthesize",
            sources=[{"url": "https://a.com"}, {"url": "https://b.com"}],
            partial_report="Partial report content...",
        )
        progress = orchestrator.get_progress(state)
        assert progress["phase"] == "synthesize"
        assert progress["progress_percent"] > 0
        assert progress["sources_count"] == 2
        assert progress["report_length"] > 0

    def test_get_progress_unknown_phase(self):
        """Given unknown phase, get_progress returns 0%."""
        mock_db = AsyncMock()
        cm = CheckpointManager(db_client=mock_db)
        orchestrator = ResumeOrchestrator(cm)
        state = ResearchState(run_id="run-123", phase="unknown_phase")
        progress = orchestrator.get_progress(state)
        assert progress["progress_percent"] == 0


class TestResearchState:
    """Tests for ResearchState data model."""

    def test_to_dict_includes_all_fields(self):
        """Given state, to_dict includes all fields."""
        state = ResearchState(
            run_id="run-123",
            phase="search",
            sources=[{"url": "https://example.com"}],
            partial_report="Partial...",
            metadata={"model": "deepseek"},
            schema_version=2,
        )
        data = state.to_dict()
        assert data["run_id"] == "run-123"
        assert data["phase"] == "search"
        assert data["schema_version"] == 2
        assert "created_at" in data

    def test_from_dict_restores_all_fields(self):
        """Given dict, from_dict restores all fields."""
        data = {
            "run_id": "run-123",
            "phase": "search",
            "sources": [{"url": "https://example.com"}],
            "partial_report": "Partial...",
            "metadata": {"model": "deepseek"},
            "schema_version": 2,
            "created_at": 1234567890.0,
        }
        state = ResearchState.from_dict(data)
        assert state.run_id == "run-123"
        assert state.phase == "search"
        assert state.schema_version == 2
        assert state.created_at == 1234567890.0

    def test_default_schema_version(self):
        """Given no schema_version, default is CURRENT_SCHEMA_VERSION."""
        state = ResearchState(run_id="run-123", phase="search")
        assert state.schema_version == CURRENT_SCHEMA_VERSION

    def test_default_created_at(self):
        """Given no created_at, default is current time."""
        state = ResearchState(run_id="run-123", phase="search")
        assert state.created_at > 0

    def test_default_sources(self):
        """Given no sources, default is empty list."""
        state = ResearchState(run_id="run-123", phase="search")
        assert state.sources == []

    def test_default_metadata(self):
        """Given no metadata, default is empty dict."""
        state = ResearchState(run_id="run-123", phase="search")
        assert state.metadata == {}
