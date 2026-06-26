"""Checkpoint manager — exhaustive implementation with serialization, validation, and resume.

Architecture:
    CheckpointManager (public interface)
    ├── StateSerializer (compression, truncation, versioning)
    ├── StateValidator (schema validation, version checking)
    ├── ResumeOrchestrator (pipeline re-entry)
    └── ResearchState (data model)
"""
from __future__ import annotations

import gzip
import json
import time
from dataclasses import dataclass, field
from typing import Any, Protocol


# ─── State Schema Version ──────────────────────────────────────────

CURRENT_SCHEMA_VERSION = 1


@dataclass
class ResearchState:
    """Serializable research run state with schema versioning."""
    run_id: str
    phase: str
    sources: list[dict] = field(default_factory=list)
    partial_report: str = ""
    metadata: dict = field(default_factory=dict)
    schema_version: int = CURRENT_SCHEMA_VERSION
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "phase": self.phase,
            "sources": self.sources,
            "partial_report": self.partial_report,
            "metadata": self.metadata,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResearchState":
        return cls(
            run_id=data["run_id"],
            phase=data["phase"],
            sources=data.get("sources", []),
            partial_report=data.get("partial_report", ""),
            metadata=data.get("metadata", {}),
            schema_version=data.get("schema_version", 1),
            created_at=data.get("created_at", time.time()),
        )


# ─── State Serializer ────────────────────────────────────────────────

class StateSerializer:
    """Serializes and deserializes ResearchState with compression.

    Uses gzip for compression, JSON for structure.
    Truncates non-essential data (full page content) to stay under size limit.
    """

    COMPRESSION_LEVEL = 6  # Balance between speed and size
    MAX_SOURCE_CONTENT_LEN = 2000  # Truncate source content to 2KB each

    def serialize(self, state: ResearchState) -> bytes:
        """Serialize state to compressed bytes."""
        data = state.to_dict()
        # Truncate source content to reduce size
        data["sources"] = self._truncate_sources(data.get("sources", []))
        json_bytes = json.dumps(data, separators=(',', ':')).encode("utf-8")
        return gzip.compress(json_bytes, compresslevel=self.COMPRESSION_LEVEL)

    def deserialize(self, data: bytes) -> ResearchState:
        """Deserialize compressed bytes to state."""
        json_bytes = gzip.decompress(data)
        data_dict = json.loads(json_bytes.decode("utf-8"))
        return ResearchState.from_dict(data_dict)

    def size(self, data: bytes) -> int:
        """Return uncompressed size of serialized data."""
        return len(gzip.decompress(data))

    def _truncate_sources(self, sources: list[dict]) -> list[dict]:
        """Truncate source content to reduce size."""
        truncated = []
        for s in sources:
            copy = dict(s)
            if "content" in copy and len(copy["content"]) > self.MAX_SOURCE_CONTENT_LEN:
                copy["content"] = copy["content"][:self.MAX_SOURCE_CONTENT_LEN] + "... [truncated]"
            truncated.append(copy)
        return truncated


# ─── State Validator ─────────────────────────────────────────────────

class StateValidationError(Exception):
    """Raised when state fails validation."""
    pass


class StateValidator:
    """Validates ResearchState for schema version and required fields."""

    REQUIRED_FIELDS = {"run_id", "phase", "schema_version"}
    VALID_PHASES = {
        "intent", "plan", "decompose", "search", "scrape",
        "validate", "synthesize", "report", "complete", "aborted",
    }

    def validate(self, state: ResearchState) -> list[str]:
        """Validate state. Returns list of errors (empty if valid)."""
        errors = []
        data = state.to_dict()

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")

        # Check schema version compatibility
        if data.get("schema_version", 1) > CURRENT_SCHEMA_VERSION:
            errors.append(
                f"Schema version {data['schema_version']} is newer than "
                f"supported version {CURRENT_SCHEMA_VERSION}. Please upgrade DRA."
            )

        # Check phase validity
        if data.get("phase") not in self.VALID_PHASES:
            errors.append(
                f"Invalid phase: {data.get('phase')}. "
                f"Valid phases: {', '.join(sorted(self.VALID_PHASES))}"
            )

        # Check sources are serializable
        try:
            json.dumps(data.get("sources", []))
        except (TypeError, ValueError) as e:
            errors.append(f"Sources contain non-serializable data: {e}")

        return errors

    def is_compatible(self, state: ResearchState) -> bool:
        """Quick check if state is compatible (no errors)."""
        return len(self.validate(state)) == 0


# ─── Checkpoint Errors ───────────────────────────────────────────────

class CheckpointTooLargeError(Exception):
    """Raised when checkpoint state exceeds size limit."""
    pass


class CheckpointNotFoundError(Exception):
    """Raised when no checkpoint exists for a run."""
    pass


# ─── Checkpoint Manager ──────────────────────────────────────────────

class CheckpointManager:
    """Manages research run checkpoints with compression and validation.

    Features:
    - Latest-only storage (keeps only most recent checkpoint per run)
    - 5MB size limit with automatic truncation
    - Gzip compression for efficient storage
    - Schema versioning for compatibility
    - TTL cleanup for old checkpoints
    """

    MAX_SIZE_BYTES = 5_242_880  # 5MB
    DEFAULT_TTL_DAYS = 7

    def __init__(
        self,
        db_client=None,
        max_size_bytes: int = MAX_SIZE_BYTES,
        serializer: StateSerializer | None = None,
        validator: StateValidator | None = None,
    ):
        self._db = db_client
        self._max_size = max_size_bytes
        self._serializer = serializer or StateSerializer()
        self._validator = validator or StateValidator()

    async def save(self, run_id: str, phase: str, state: ResearchState) -> dict:
        """Save a checkpoint. Deletes previous checkpoint for same run.

        Args:
            run_id: Research run ID
            phase: Current phase (e.g., 'synthesize', 'search')
            state: ResearchState to checkpoint

        Returns:
            Dict with checkpoint metadata

        Raises:
            CheckpointTooLargeError: If serialized state exceeds max_size
            StateValidationError: If state fails validation
        """
        # Validate state before saving
        errors = self._validator.validate(state)
        if errors:
            raise StateValidationError(f"State validation failed: {errors}")

        # Serialize and compress
        serialized = self._serializer.serialize(state)
        size = len(serialized)

        if size > self._max_size:
            raise CheckpointTooLargeError(
                f"Serialized state size {size} bytes exceeds "
                f"{self._max_size} bytes. Consider truncating source content."
            )

        # In-memory fallback if no DB client
        if self._db is None:
            return {
                "run_id": run_id,
                "phase": phase,
                "size": size,
                "compressed": True,
            }

        # Delete old checkpoint for this run (latest-only policy)
        await self._db.delete_old_checkpoints(run_id)

        # Insert new checkpoint
        checkpoint = await self._db.insert_checkpoint(
            run_id=run_id,
            phase=phase,
            state_data=serialized,  # Compressed bytes
            size_bytes=size,
            created_at=time.time(),
        )
        return checkpoint

    async def load_latest(self, run_id: str) -> ResearchState | None:
        """Load the latest checkpoint for a run.

        Returns:
            ResearchState if checkpoint exists, None otherwise
        """
        if self._db is None:
            return None

        result = await self._db.get_latest_checkpoint(run_id)
        if not result:
            return None

        # Decompress and deserialize
        state_data = result.get("state_data") or result.get("state_json", "").encode()
        if isinstance(state_data, str):
            state_data = state_data.encode()

        try:
            state = self._serializer.deserialize(state_data)
        except Exception as e:
            raise StateValidationError(f"Failed to deserialize checkpoint: {e}")

        # Validate loaded state
        errors = self._validator.validate(state)
        if errors:
            raise StateValidationError(f"Loaded state validation failed: {errors}")

        return state

    async def resume(self, run_id: str) -> ResearchState:
        """Resume a run from its latest checkpoint.

        Args:
            run_id: Research run ID

        Returns:
            ResearchState at last checkpoint

        Raises:
            CheckpointNotFoundError: If no checkpoint exists
            StateValidationError: If checkpoint is invalid
        """
        state = await self.load_latest(run_id)
        if state is None:
            raise CheckpointNotFoundError(f"No checkpoint found for run {run_id}")
        return state

    async def cleanup_old(self, days: int = DEFAULT_TTL_DAYS) -> int:
        """Delete checkpoints older than N days.

        Returns:
            Number of checkpoints deleted
        """
        if self._db is None:
            return 0

        cutoff = time.time() - (days * 24 * 60 * 60)
        return await self._db.delete_checkpoints_before(cutoff)

    async def list_checkpoints(self, run_id: str) -> list[dict]:
        """List all checkpoints for a run (for debugging)."""
        if self._db is None:
            return []
        return await self._db.get_checkpoints(run_id)

    async def get_stats(self) -> dict[str, Any]:
        """Get checkpoint storage statistics."""
        if self._db is None:
            return {"total": 0, "total_size": 0}
        return await self._db.get_checkpoint_stats()


# ─── Resume Orchestrator ─────────────────────────────────────────────

class ResumeOrchestrator:
    """Orchestrates resuming a research run from a checkpoint.

    Re-enters the research pipeline at the correct phase.
    """

    PHASE_ORDER = [
        "intent", "plan", "decompose", "search", "scrape",
        "validate", "synthesize", "report", "complete",
    ]

    def __init__(self, checkpoint_manager: CheckpointManager):
        self._cm = checkpoint_manager

    async def can_resume(self, run_id: str) -> bool:
        """Check if a run can be resumed."""
        try:
            state = await self._cm.load_latest(run_id)
            return state is not None
        except Exception:
            return False

    async def resume(self, run_id: str) -> tuple[ResearchState, str]:
        """Resume a run and return state + next phase.

        Returns:
            Tuple of (ResearchState, next_phase_to_execute)
        """
        state = await self._cm.resume(run_id)

        # Determine next phase based on current phase
        current_phase = state.phase
        if current_phase == "complete":
            return state, "complete"  # Already done

        try:
            idx = self.PHASE_ORDER.index(current_phase)
            next_phase = self.PHASE_ORDER[idx]  # Re-run current phase (retry)
        except ValueError:
            next_phase = "search"  # Unknown phase, default to search

        return state, next_phase

    def get_progress(self, state: ResearchState) -> dict[str, Any]:
        """Compute progress percentage from phase."""
        try:
            idx = self.PHASE_ORDER.index(state.phase)
            pct = (idx / len(self.PHASE_ORDER)) * 100
        except ValueError:
            pct = 0

        return {
            "phase": state.phase,
            "progress_percent": round(pct, 1),
            "sources_count": len(state.sources),
            "report_length": len(state.partial_report),
        }
