"""Exhaustive tests for SSE events with pipeline integration."""
import time
import pytest

from research_engine.sse.events import (
    SSEEvent,
    EventBuffer,
    ResearchStream,
)


class TestSSEEvent:
    """Tests for SSE event structure."""

    def test_event_has_required_fields(self):
        """Given event, has all required fields."""
        event = SSEEvent(
            event_id=1,
            event_type="citation_verification",
            phase="citation_verification",
            status="progress",
            data={"verified": 15, "total": 50, "percentage": 30},
            run_id="run-123",
        )
        assert event.event_id == 1
        assert event.phase == "citation_verification"
        assert event.status == "progress"
        assert "verified" in event.data
        assert event.run_id == "run-123"

    def test_events_are_ordered_by_event_id(self):
        """Given multiple events, ordered by event_id."""
        events = [
            SSEEvent(event_id=3, event_type="review", phase="review", status="done", data={}),
            SSEEvent(event_id=1, event_type="cv", phase="citation_verification", status="start", data={}),
            SSEEvent(event_id=2, event_type="cv", phase="citation_verification", status="progress", data={}),
        ]
        sorted_events = sorted(events, key=lambda e: e.event_id)
        assert sorted_events[0].event_id == 1
        assert sorted_events[1].event_id == 2
        assert sorted_events[2].event_id == 3

    def test_to_sse_line_format(self):
        """Given event, to_sse_line returns valid SSE format."""
        event = SSEEvent(
            event_id=1,
            event_type="test",
            phase="test",
            status="ok",
            data={"msg": "hello"},
        )
        line = event.to_sse_line()
        assert line.startswith("id: 1")
        assert "event: test" in line
        assert "data:" in line

    def test_to_dict_serialization(self):
        """Given event, to_dict returns correct dict."""
        event = SSEEvent(
            event_id=42,
            event_type="phase",
            phase="search",
            status="done",
            data={"sources": 10},
            run_id="run-123",
        )
        d = event.to_dict()
        assert d["id"] == 42
        assert d["type"] == "phase"
        assert d["phase"] == "search"
        assert d["run_id"] == "run-123"


class TestEventBuffer:
    """Tests for event buffer."""

    def test_add_increments_size(self):
        """Given event, buffer size increases."""
        buffer = EventBuffer()
        buffer.add(SSEEvent(event_id=1, event_type="test", phase="test", status="ok", data={}))
        assert len(buffer) == 1

    def test_flush_returns_events(self):
        """Given buffered events, flush returns them."""
        buffer = EventBuffer()
        event = SSEEvent(event_id=1, event_type="test", phase="test", status="ok", data={})
        buffer.add(event)
        flushed = buffer.flush()
        assert len(flushed) == 1
        assert flushed[0] == event

    def test_flush_clears_buffer(self):
        """Given flush, buffer is cleared."""
        buffer = EventBuffer()
        buffer.add(SSEEvent(event_id=1, event_type="test", phase="test", status="ok", data={}))
        buffer.flush()
        assert len(buffer) == 0

    def test_max_size_limits_buffer(self):
        """Given max size, buffer limits events."""
        buffer = EventBuffer(max_size=3)
        for i in range(5):
            buffer.add(SSEEvent(event_id=i, event_type="test", phase="test", status="ok", data={}))
        assert len(buffer) == 3

    def test_max_size_keeps_recent(self):
        """Given max size, keeps most recent events."""
        buffer = EventBuffer(max_size=3)
        for i in range(5):
            buffer.add(SSEEvent(event_id=i, event_type="test", phase="test", status="ok", data={}))
        flushed = buffer.flush()
        ids = [e.event_id for e in flushed]
        assert ids == [2, 3, 4]


class TestResearchStream:
    """Tests for research stream with pipeline integration."""

    def test_stream_increments_event_id(self):
        """Given multiple events, IDs auto-increment."""
        stream = ResearchStream()
        e1 = stream.next_event("phase", "search", "start", {})
        e2 = stream.next_event("phase", "scrape", "done", {})
        assert e1.event_id == 1
        assert e2.event_id == 2

    def test_phase_event(self):
        """Given phase_event, creates phase-specific event."""
        stream = ResearchStream()
        event = stream.phase_event("search", "start", {"query": "AI"})
        assert event.event_type == "phase"
        assert event.phase == "search"
        assert event.status == "start"
        assert event.data["query"] == "AI"

    def test_progress_event(self):
        """Given progress_event, includes percentage."""
        stream = ResearchStream()
        event = stream.progress_event("search", 5, 10, "Finding sources")
        assert event.event_type == "progress"
        assert event.data["current"] == 5
        assert event.data["total"] == 10
        assert event.data["percentage"] == 50.0
        assert event.data["message"] == "Finding sources"

    def test_progress_event_zero_total(self):
        """Given zero total, percentage is 0."""
        stream = ResearchStream()
        event = stream.progress_event("search", 0, 0)
        assert event.data["percentage"] == 0

    def test_heartbeat_event(self):
        """Given heartbeat, returns keepalive event."""
        stream = ResearchStream(heartbeat_interval=0)
        time.sleep(0.01)
        hb = stream.heartbeat()
        assert hb is not None
        assert hb.event_type == "heartbeat"
        assert hb.phase == "keepalive"
        assert hb.status == "ok"
        assert "timestamp" in hb.data

    def test_heartbeat_not_due(self):
        """Given heartbeat not due, returns None."""
        stream = ResearchStream(heartbeat_interval=30)
        hb = stream.heartbeat()
        assert hb is None

    def test_should_send_heartbeat(self):
        """Given elapsed interval, should_send_heartbeat is True."""
        stream = ResearchStream(heartbeat_interval=0)
        time.sleep(0.01)
        assert stream.should_send_heartbeat() is True

    def test_should_send_heartbeat_not_due(self):
        """Given not elapsed, should_send_heartbeat is False."""
        stream = ResearchStream(heartbeat_interval=30)
        assert stream.should_send_heartbeat() is False

    def test_error_event(self):
        """Given error_event, creates error event."""
        stream = ResearchStream()
        event = stream.error_event("search", "Connection timeout", {"retry": 1})
        assert event.event_type == "error"
        assert event.phase == "search"
        assert event.status == "error"
        assert event.data["error"] == "Connection timeout"
        assert event.data["retry"] == 1

    def test_complete_event(self):
        """Given complete_event, creates completion event."""
        stream = ResearchStream()
        event = stream.complete_event({"report": "Done"})
        assert event.event_type == "complete"
        assert event.phase == "complete"
        assert event.status == "done"
        assert event.data["result"]["report"] == "Done"
        assert "phases_completed" in event.data

    def test_get_progress_no_phases(self):
        """Given no phases, progress is 0."""
        stream = ResearchStream()
        progress = stream.get_progress()
        assert progress["phase"] == "starting"
        assert progress["percent"] == 0

    def test_get_progress_with_phases(self):
        """Given phases, progress is computed."""
        stream = ResearchStream()
        stream.phase_event("search", "done")
        stream.phase_event("scrape", "done")
        progress = stream.get_progress()
        assert progress["phase"] == "scrape"
        assert progress["percent"] > 0
        assert progress["events_emitted"] > 0

    def test_get_progress_unknown_phase(self):
        """Given unknown phase, progress is 0."""
        stream = ResearchStream()
        stream.next_event("test", "unknown_phase", "done", {})
        progress = stream.get_progress()
        assert progress["percent"] == 0

    def test_flush_buffer(self):
        """Given buffered events, flush returns them."""
        stream = ResearchStream()
        stream.phase_event("search", "done")
        stream.phase_event("scrape", "done")
        flushed = stream.flush_buffer()
        assert len(flushed) == 2

    def test_run_id_propagation(self):
        """Given run_id, propagated to all events."""
        stream = ResearchStream(run_id="run-456")
        event = stream.phase_event("search", "done")
        assert event.run_id == "run-456"

    def test_phase_tracking(self):
        """Given phase events, tracks unique phases."""
        stream = ResearchStream()
        stream.phase_event("search", "done")
        stream.phase_event("search", "done")  # Duplicate
        stream.phase_event("scrape", "done")
        progress = stream.get_progress()
        assert len(progress["phases_completed"]) == 2

    def test_all_phase_types(self):
        """Given all phase types, tracked correctly."""
        stream = ResearchStream()
        for phase in stream.PHASE_ORDER:
            stream.phase_event(phase, "done")
        progress = stream.get_progress()
        assert progress["phase"] == "complete"
        assert progress["percent"] == pytest.approx(88.9, 0.1)  # 8/9 * 100
