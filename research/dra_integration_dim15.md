# Dimension 15: SSE Event Architecture & Real-Time Streaming

## Overview

This dimension investigates the technical implications of adding new SSE (Server-Sent Events) events for citation verification and review phases. It covers event ordering, client state management, backpressure, and integration with the existing SSE stream architecture.

---

## Key Findings

### 1. New SSE Events Require Client State Machine Updates

**Claim:** The DRA plan proposes 4 new SSE events: `citation_verification_start`, `citation_verification_complete`, `review_start`, `review_complete`. The frontend's `ResearchProgress` component must handle these events in the correct order, updating the progress bar and status text.[^1]

**Source:** DRA Integration Plan (SSE Events specification)

**URL:** File: D:\Projects\ai-ml\DeepResearchAgent\research\dra_integration_plan.md

**Date:** 2026

**Excerpt:**
> "Emit SSE events: citation_verification_start, citation_verification_complete, review_start, review_complete."

**Context:** DRA's existing SSE stream already has events for: `classify`, `plan`, `decompose`, `search`, `scrape`, `validate`, `synthesize`, `mindmap`. The new events fit between `synthesize` and `mindmap`:

```
Existing:  classify → plan → decompose → search → scrape → validate → synthesize → mindmap
New:      classify → plan → decompose → search → scrape → validate → synthesize → citation_verify → review → mindmap
```

The frontend's progress calculation assumes a fixed number of phases. Adding 2 new phases changes the progress percentage calculation. For example, if the existing pipeline has 8 phases and progress is calculated as `completed_phases / 8 * 100`, adding 2 phases means the denominator changes to 10. The frontend must be updated to handle this dynamically.

**Confidence:** High

---

**Claim:** The `EventSource` API (SSE client) has a default reconnection delay of 3 seconds. If a citation verification event is lost during a reconnection, the client may miss the `citation_verification_complete` event and remain in a loading state indefinitely.[^2]

**Source:** MDN EventSource Documentation

**URL:** https://developer.mozilla.org/en-US/docs/Web/API/EventSource

**Date:** 2026

**Excerpt:**
> "If the connection is closed, the browser will automatically attempt to reconnect. The reconnection time can be controlled by the server sending a retry field."

**Context:** SSE streams are reliable for short events but can lose events during reconnections. The DRA plan should include an `event_id` field in each SSE event so the client can detect missed events and request a state refresh. Alternatively, the client should poll the API for current run status after reconnection rather than relying solely on SSE events.

**Recommendation:** Add `event_id` (monotonically increasing) and `phase` (current phase name) to every SSE event:

```json
{
  "event_id": 42,
  "phase": "citation_verification",
  "status": "complete",
  "data": { ... }
}
```

**Confidence:** High

---

### 2. SSE Backpressure with Long-Running Operations

**Claim:** Citation verification can take 30-150 seconds for a large report (50+ citations, 4 APIs). During this time, the SSE connection must remain open. If the client disconnects (browser close, network change), the server continues processing but the client loses progress updates.[^3]

**Source:** SSE Backpressure Patterns (Node.js/Streaming)

**URL:** https://nodejs.org/api/stream.html#backpressure

**Date:** 2026

**Excerpt:**
> "Backpressure is the mechanism by which a data consumer can signal to a data producer that it is overwhelmed and should slow down or stop sending data."

**Context:** FastAPI's SSE implementation uses `StreamingResponse` which buffers events in memory. If the client disconnects, the server may continue writing to a closed connection, causing `ConnectionResetError` exceptions. The DRA plan should:
1. Catch connection errors gracefully in the SSE handler
2. Use `request.is_disconnected()` to check client status before sending events
3. Save progress to the database so the client can resume on reconnection

```python
# In api.py SSE handler
async def event_stream(run_id: UUID):
    async for event in orchestrator.run_research(run_id):
        if await request.is_disconnected():
            break  # Stop processing if client disconnected
        yield f"data: {json.dumps(event)}\n\n"
```

**Confidence:** High

---

### 3. Event Ordering and Idempotency

**Claim:** The DRA plan's new events must be ordered correctly: `citation_verification_start` → `citation_verification_complete` → `review_start` → `review_complete`. If events arrive out of order (e.g., due to network latency), the frontend may show incorrect status.[^4]

**Source:** DRA Orchestrator Analysis

**URL:** File: D:\Projects\ai-ml\DeepResearchAgent\research\dra_integration_plan.md

**Date:** 2026

**Excerpt:**
> "synthesize → citation_verify → review → mindmap"

**Context:** SSE events are guaranteed to be delivered in order over a single connection, but if the client reconnects, it may receive events from a different starting point. The frontend should not rely on event order alone but should track the current phase independently. For example, if the client receives `review_complete` before `citation_verification_start`, it should treat this as a state update ("we're at review phase") rather than an error.

**Recommendation:** Use a state machine on the frontend that tracks the current phase rather than assuming event order:

```typescript
// Frontend state machine
const phases = ['classify', 'plan', 'decompose', 'search', 'scrape', 'validate', 'synthesize', 'citation_verify', 'review', 'mindmap'];

const currentPhaseIndex = phases.indexOf(event.phase);
const progress = (currentPhaseIndex / phases.length) * 100;
```

**Confidence:** High

---

### 4. Client-Side Event Buffering

**Claim:** The frontend should buffer SSE events to handle bursts. For example, during citation verification, the server may emit per-citation progress events (e.g., "5 of 50 citations verified"). If the client cannot process these events fast enough, the browser's event queue may drop events.[^5]

**Source:** Browser Event Loop Performance

**URL:** https://developer.mozilla.org/en-US/docs/Web/JavaScript/EventLoop

**Date:** 2026

**Excerpt:**
> "The event loop is the mechanism that allows JavaScript to perform non-blocking operations despite being single-threaded."

**Context:** The DRA plan does not mention per-citation progress events, but they would be useful for user feedback. However, emitting 50 events for 50 citations would create an event burst. The frontend should:
1. Throttle event processing (e.g., process at most 1 event per 100ms)
2. Batch events (e.g., "verified 5, 10, 15, 20 citations" instead of individual events)
3. Use `requestAnimationFrame` for UI updates to avoid blocking the main thread

**Recommendation:** Add batch progress events:
```json
{
  "phase": "citation_verification",
  "status": "progress",
  "progress": {
    "verified": 15,
    "total": 50,
    "percentage": 30
  }
}
```

**Confidence:** High

---

## Tensions and Counter-Arguments

### Tension 1: SSE vs. WebSockets for Real-Time Updates

SSE is one-way (server to client) and uses HTTP. WebSockets are bidirectional and use a persistent TCP connection. For DRA's use case, SSE is sufficient because the client only needs to receive progress updates. However, if the client needs to send commands (e.g., "abort citation verification"), WebSockets would be more appropriate.

**Counter-argument:** SSE is the right choice for DRA. The existing architecture already uses SSE, and the new events fit the same pattern. Adding WebSockets would require significant refactoring. For abort functionality, the client can use a separate HTTP endpoint (`POST /research/abort`).

### Tension 2: Event Verbosity vs. Bandwidth

Detailed events (per-citation progress) provide better UX but consume more bandwidth. For a 50-citation report with 10 events per citation (start, CrossRef query, OpenAlex query, Semantic Scholar query, arXiv query, scoring, complete), that's 500 events per report. With 1000 concurrent users, that's 500,000 events.

**Counter-argument:** Use batch events for high-frequency updates. Emit per-citation events only for the first 5 citations (to show the user what's happening), then switch to batch events for the remaining citations. This balances UX and bandwidth.

### Tension 3: Graceful Degradation Without SSE

If the client's browser does not support SSE (older browsers) or the connection is blocked (corporate firewalls), the frontend should fall back to polling.

**Counter-argument:** The DRA plan should specify a fallback polling mechanism:
1. Attempt SSE connection
2. If SSE fails, fall back to `GET /research/{run_id}/status` polled every 5 seconds
3. Show a warning: "Real-time updates unavailable. Refreshing every 5 seconds."

This ensures the feature works even in restricted environments.

---

## Recommendations

### 1. Add Event IDs and Phase Tracking

```python
# In orchestrator.py
class Orchestrator:
    _event_counter = 0
    
    async def _emit_event(self, run_id: UUID, phase: str, status: str, data: dict = None):
        self._event_counter += 1
        event = {
            "event_id": self._event_counter,
            "run_id": str(run_id),
            "phase": phase,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {}
        }
        await self._sse_queue.put(event)
        return event
```

### 2. Implement Batch Progress Events

```python
# Citation verification batch events
async def verify_citations_batch(self, citations: list[Citation]):
    total = len(citations)
    batch_size = max(1, total // 10)  # 10 progress updates max
    
    for i, citation in enumerate(citations):
        result = await self.verify(citation)
        
        # Emit batch progress every N citations
        if i % batch_size == 0 or i == total - 1:
            await self._emit_event(
                run_id=self.run_id,
                phase="citation_verification",
                status="progress",
                data={"verified": i + 1, "total": total, "percentage": ((i + 1) / total) * 100}
            )
```

### 3. Add Connection Health Checks

```python
# In SSE handler
async def research_stream(request: Request, run_id: UUID):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                logger.info(f"Client disconnected for run {run_id}")
                break
            
            try:
                event = await asyncio.wait_for(
                    sse_queue.get(run_id),
                    timeout=30.0  # Heartbeat every 30s
                )
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 4. Frontend Fallback to Polling

```typescript
// client.ts
async function streamResearch(runId: string, onEvent: (event: SSEEvent) => void) {
  try {
    const eventSource = new EventSource(`/research/stream?run_id=${runId}`);
    eventSource.onmessage = (e) => onEvent(JSON.parse(e.data));
    eventSource.onerror = () => {
      eventSource.close();
      // Fall back to polling
      startPolling(runId, onEvent);
    };
  } catch (e) {
    // SSE not supported, fall back to polling
    startPolling(runId, onEvent);
  }
}

function startPolling(runId: string, onEvent: (event: SSEEvent) => void) {
  const interval = setInterval(async () => {
    const status = await api.getRunStatus(runId);
    onEvent(status);
  }, 5000);
  
  // Stop polling when run completes
  return () => clearInterval(interval);
}
```

---

## Confidence Assessment

| Finding | Confidence |
|---------|------------|
| New events require client state machine updates | High |
| SSE can lose events during reconnection | High |
| Backpressure handling needed for long operations | High |
| Event ordering must be handled gracefully | High |
| Batch events reduce bandwidth for high-frequency updates | High |

---

## Sources

[^1]: DRA Integration Plan (SSE Events). 2026. File: dra_integration_plan.md

[^2]: MDN EventSource Documentation. 2026. https://developer.mozilla.org/en-US/docs/Web/API/EventSource

[^3]: Node.js Stream Backpressure. 2026. https://nodejs.org/api/stream.html#backpressure

[^4]: DRA Orchestrator Analysis. 2026. File: dra_integration_plan.md

[^5]: MDN JavaScript Event Loop. 2026. https://developer.mozilla.org/en-US/docs/Web/JavaScript/EventLoop

