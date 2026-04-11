import type {
  RunSummary,
  MindmapGraph,
  NodeExpansion,
  ResearchRequest,
  ResearchEvent,
  PlanPreview,
  PlanApproval,
  ExportFormatInfo,
  KnowledgeGraph,
  KGQueryRequest,
  KGQueryResult,
  KGMcpStatus,
  KGAvailability,
} from '../types/api';


const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  /**
   * List all past research runs, newest first.
   */
  async listRuns(): Promise<RunSummary[]> {
    const res = await fetch(`${BASE_URL}/runs`);
    return handleResponse<RunSummary[]>(res);
  },

  /**
   * Get the Markdown report for a research run.
   */
  async getReport(runId: string): Promise<string> {
    const res = await fetch(`${BASE_URL}/runs/${runId}/report`);
    if (!res.ok) throw new Error('Failed to fetch report');
    const data = await res.json();
    return data.content || '';
  },

  /**
   * Get the mindmap graph (G6 format) for a research run.
   */
  async getMindmap(runId: string): Promise<MindmapGraph> {
    const res = await fetch(`${BASE_URL}/runs/${runId}/mindmap`);
    return handleResponse<MindmapGraph>(res);
  },

  /**
   * Expand a mindmap node — drill deeper.
   */
  async expandNode(runId: string, nodeId: string): Promise<NodeExpansion> {
    const res = await fetch(`${BASE_URL}/runs/${runId}/mindmap/expand`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ node_id: nodeId }),
    });
    return handleResponse<NodeExpansion>(res);
  },

  /**
   * Start a new research run (blocking). Returns run_id.
   */
  async startResearch(req: ResearchRequest): Promise<{ run_id: string }> {
    const res = await fetch(`${BASE_URL}/research`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse<{ run_id: string }>(res);
  },

  /**
   * Stream research via SSE (Phase 2).
   *
   * Uses fetch + ReadableStream (not EventSource, since we need POST).
   * Returns an AbortController for cleanup.
   */
  streamResearch(
    req: ResearchRequest,
    onEvent: (event: ResearchEvent) => void,
    onDone: (data: Record<string, any>) => void,
    onError: (error: string) => void,
  ): AbortController {
    const controller = new AbortController();

    const run = async () => {
      try {
        const res = await fetch(`${BASE_URL}/research/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req),
          signal: controller.signal,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(body.detail || `Stream failed: ${res.status}`);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE frames from buffer
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          let currentEvent = 'message';
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim();
              try {
                const data = JSON.parse(dataStr);
                const event: ResearchEvent = { event: currentEvent, data };
                onEvent(event);

                if (currentEvent === 'complete') {
                  onDone(data);
                  return;
                }
                if (currentEvent === 'error') {
                  onError(data.error || 'Unknown error');
                }
              } catch {
                // Ignore malformed JSON
              }
              currentEvent = 'message'; // Reset after processing
            }
            // Ignore comments (heartbeats starting with ':')
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;
        onError(err instanceof Error ? err.message : 'Stream failed');
      }
    };

    run();
    return controller;
  },

  /**
   * Generate a research plan for user review (Phase 4).
   */
  async generatePlan(req: ResearchRequest): Promise<PlanPreview> {
    const res = await fetch(`${BASE_URL}/research/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse<PlanPreview>(res);
  },

  /**
   * Execute a user-approved plan with SSE streaming (Phase 4).
   */
  streamApprovedPlan(
    approval: PlanApproval,
    onEvent: (event: ResearchEvent) => void,
    onDone: (data: Record<string, any>) => void,
    onError: (error: string) => void,
  ): AbortController {
    const controller = new AbortController();

    const run = async () => {
      try {
        const res = await fetch(`${BASE_URL}/research/execute/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(approval),
          signal: controller.signal,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(body.detail || `Stream failed: ${res.status}`);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          let currentEvent = 'message';
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim();
              try {
                const data = JSON.parse(dataStr);
                const event: ResearchEvent = { event: currentEvent, data };
                onEvent(event);

                if (currentEvent === 'complete') {
                  onDone(data);
                  return;
                }
              } catch {
                // Ignore
              }
              currentEvent = 'message';
            }
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;
        onError(err instanceof Error ? err.message : 'Stream failed');
      }
    };

    run();
    return controller;
  },

  /**
   * Download a research export (Phase 5).
   */
  async exportRun(runId: string, format: string): Promise<Blob> {
    const res = await fetch(`${BASE_URL}/runs/${runId}/export/${format}`);
    if (!res.ok) throw new Error(`Export failed: ${res.statusText}`);
    return res.blob();
  },

  /**
   * List available export formats for a run (Phase 5).
   */
  async listExports(runId: string): Promise<{ run_id: string; formats: ExportFormatInfo[] }> {
    const res = await fetch(`${BASE_URL}/runs/${runId}/exports`);
    return handleResponse<{ run_id: string; formats: ExportFormatInfo[] }>(res);
  },

  /**
   * Validate an OpenRouter model ID.
   */
  async validateModel(model: string): Promise<{ valid: boolean; error?: string }> {
    const res = await fetch(`${BASE_URL}/validate-model`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model }),
    });
    return res.json();
  },

  // ──── Knowledge Graph (Graphify) ────────────────────────────────────

  /** Get the knowledge graph for a run. Throws 404 if not built. */
  async getKnowledgeGraph(runId: string): Promise<KnowledgeGraph> {
    const res = await fetch(`${BASE_URL}/runs/${runId}/knowledge-graph`);
    return handleResponse<KnowledgeGraph>(res);
  },

  /** Check KG + graph.html availability for a run (non-throwing). */
  async getKnowledgeGraphAvailability(runId: string): Promise<KGAvailability> {
    const res = await fetch(`${BASE_URL}/runs/${runId}/knowledge-graph/available`);
    return handleResponse<KGAvailability>(res);
  },

  /** Trigger manual KG build for an existing run. */
  async buildKnowledgeGraph(runId: string): Promise<KnowledgeGraph> {
    const res = await fetch(`${BASE_URL}/runs/${runId}/knowledge-graph/build`, {
      method: 'POST',
    });
    return handleResponse<KnowledgeGraph>(res);
  },

  /** Query the knowledge graph with BFS/DFS traversal. */
  async queryKnowledgeGraph(runId: string, req: KGQueryRequest): Promise<KGQueryResult> {
    const res = await fetch(`${BASE_URL}/runs/${runId}/knowledge-graph/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse<KGQueryResult>(res);
  },

  /** Get a direct URL to the interactive graph.html (open in new tab). */
  getGraphHtmlUrl(runId: string): string {
    return `${BASE_URL}/runs/${runId}/knowledge-graph/html`;
  },

  /** Get MCP server status. */
  async getMcpStatus(runId: string): Promise<KGMcpStatus> {
    const res = await fetch(`${BASE_URL}/runs/${runId}/knowledge-graph/mcp`);
    return handleResponse<KGMcpStatus>(res);
  },

  /** Start Graphify MCP server for a run. */
  async startMcpServer(runId: string): Promise<{ status: string }> {
    const res = await fetch(`${BASE_URL}/runs/${runId}/knowledge-graph/mcp/start`, {
      method: 'POST',
    });
    return handleResponse<{ status: string }>(res);
  },

  /** Stop Graphify MCP server for a run. */
  async stopMcpServer(runId: string): Promise<{ status: string }> {
    const res = await fetch(`${BASE_URL}/runs/${runId}/knowledge-graph/mcp/stop`, {
      method: 'POST',
    });
    return handleResponse<{ status: string }>(res);
  },

  // ──── GitNexus Code Architecture ─────────────────────────────────────

  /** Get the GitNexus codebase architecture graph (cached or freshly built). */
  async getGitnexusGraph(): Promise<KnowledgeGraph> {
    const res = await fetch(`${BASE_URL}/gitnexus/graph`);
    return handleResponse<KnowledgeGraph>(res);
  },

  /** Trigger npx gitnexus analyze + graph rebuild in the background. */
  async triggerGitnexusAnalyze(): Promise<{ status: string; message: string }> {
    const res = await fetch(`${BASE_URL}/gitnexus/analyze`, { method: 'POST' });
    return handleResponse<{ status: string; message: string }>(res);
  },

  /** Get GitNexus eval-server reachability, scheduler state, and graph age. */
  async getGitnexusStatus(): Promise<{
    eval_server_running: boolean;
    scheduler_running: boolean;
    graph_cached: boolean;
    graph_age_seconds: number | null;
    graph_path: string;
  }> {
    const res = await fetch(`${BASE_URL}/gitnexus/status`);
    return handleResponse(res);
  },
};

