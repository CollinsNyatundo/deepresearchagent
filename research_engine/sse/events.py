"""SSE events — exhaustive implementation with pipeline integration.

Features:
- SSEEvent with proper formatting
- ResearchStream with auto-incrementing IDs
- Heartbeat mechanism with configurable interval
- Event buffering for batch emission
- Pipeline integration for research phases
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator


@dataclass(frozen=True)
class SSEEvent:
    """Base SSE event for research stream."""
    event_id: int
    event_type: str
    phase: str
    status: str
    data: dict[str, Any]
    run_id: str = ""

    def to_sse_line(self) -> str:
        """Format as SSE event line."""
        lines = [
            f"id: {self.event_id}",
            f"event: {self.event_type}",
            f"data: {json.dumps(self.data)}",
            "",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "id": self.event_id,
            "type": self.event_type,
            "phase": self.phase,
            "status": self.status,
            "data": self.data,
            "run_id": self.run_id,
        }


@dataclass
class EventBuffer:
    """Buffer for batching SSE events."""

    max_size: int = 100
    _events: list[SSEEvent] = field(default_factory=list)

    def add(self, event: SSEEvent) -> None:
        """Add event to buffer."""
        self._events.append(event)
        if len(self._events) > self.max_size:
            self._events = self._events[-self.max_size:]

    def flush(self) -> list[SSEEvent]:
        """Return and clear all buffered events."""
        events = self._events.copy()
        self._events.clear()
        return events

    def __len__(self) -> int:
        return len(self._events)


@dataclass
class ResearchStream:
    """Manages SSE event stream with heartbeat and buffering.

    Features:
    - Auto-incrementing event IDs
    - Configurable heartbeat interval
    - Event buffering for batch operations
    - Pipeline phase tracking
    """

    heartbeat_interval: int = 30
    run_id: str = ""
    _event_counter: int = field(default=0, init=False)
    _buffer: EventBuffer = field(default_factory=lambda: EventBuffer(), init=False)
    _last_heartbeat: float = field(default_factory=time.time, init=False)
    _phases: list[str] = field(default_factory=list, init=False)

    PHASE_ORDER = [
        "intent", "plan", "decompose", "search", "scrape",
        "validate", "synthesize", "report", "complete",
    ]

    def next_event(self, event_type: str, phase: str, status: str, data: dict) -> SSEEvent:
        """Create next event with auto-incrementing ID."""
        self._event_counter += 1
        event = SSEEvent(
            event_id=self._event_counter,
            event_type=event_type,
            phase=phase,
            status=status,
            data=data,
            run_id=self.run_id,
        )
        self._buffer.add(event)
        self._track_phase(phase)
        return event

    def phase_event(self, phase: str, status: str, data: dict | None = None) -> SSEEvent:
        """Create a phase-specific event."""
        return self.next_event(
            event_type="phase",
            phase=phase,
            status=status,
            data=data or {},
        )

    def progress_event(self, phase: str, current: int, total: int, message: str = "") -> SSEEvent:
        """Create a progress event."""
        return self.next_event(
            event_type="progress",
            phase=phase,
            status="progress",
            data={
                "current": current,
                "total": total,
                "percentage": round((current / total) * 100, 1) if total > 0 else 0,
                "message": message,
            },
        )

    def heartbeat(self) -> SSEEvent | None:
        """Create a heartbeat event if interval has elapsed.

        Returns:
            SSEEvent if heartbeat is due, None otherwise
        """
        now = time.time()
        if now - self._last_heartbeat < self.heartbeat_interval:
            return None
        self._last_heartbeat = now
        self._event_counter += 1
        return SSEEvent(
            event_id=self._event_counter,
            event_type="heartbeat",
            phase="keepalive",
            status="ok",
            data={"timestamp": now, "elapsed": round(now - self._start_time(), 1)},
            run_id=self.run_id,
        )

    def error_event(self, phase: str, error: str, details: dict | None = None) -> SSEEvent:
        """Create an error event."""
        data = {"error": error}
        if details:
            data.update(details)
        return self.next_event(
            event_type="error",
            phase=phase,
            status="error",
            data=data,
        )

    def complete_event(self, result: dict) -> SSEEvent:
        """Create a completion event."""
        return self.next_event(
            event_type="complete",
            phase="complete",
            status="done",
            data={
                "result": result,
                "phases_completed": self._phases,
                "total_events": self._event_counter,
            },
        )

    def should_send_heartbeat(self) -> bool:
        """Check if heartbeat should be sent."""
        return time.time() - self._last_heartbeat >= self.heartbeat_interval

    def get_progress(self) -> dict[str, Any]:
        """Get current progress information."""
        if not self._phases:
            return {"phase": "starting", "percent": 0}
        current_phase = self._phases[-1]
        try:
            idx = self.PHASE_ORDER.index(current_phase)
            pct = round((idx / len(self.PHASE_ORDER)) * 100, 1)
        except ValueError:
            pct = 0
        return {
            "phase": current_phase,
            "percent": pct,
            "events_emitted": self._event_counter,
            "phases_completed": self._phases,
        }

    def flush_buffer(self) -> list[SSEEvent]:
        """Flush buffered events."""
        return self._buffer.flush()

    def _track_phase(self, phase: str) -> None:
        """Track phase transitions."""
        if phase not in self._phases:
            self._phases.append(phase)

    def _start_time(self) -> float:
        """Get stream start time (approximated)."""
        return self._last_heartbeat - self.heartbeat_interval

    async def stream_events(
        self,
        event_generator: AsyncGenerator[SSEEvent, None],
    ) -> AsyncGenerator[str, None]:
        """Stream events with heartbeat injection.

        Args:
            event_generator: Async generator of SSEEvent

        Yields:
            Formatted SSE lines
        """
        async for event in event_generator:
            yield event.to_sse_line()

            # Check if heartbeat is due
            hb = self.heartbeat()
            if hb:
                yield hb.to_sse_line()
