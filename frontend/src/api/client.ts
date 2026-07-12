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
  ResearchResult,
  TelemetryResponse,
  Note,
  NoteSummary,
  NoteSearchResponse,
  DocumentListResponse,
  DocumentQueryResponse,
  OpenKBStatus,
  SkillResponse,
  SkillListResponse,
  WikiPageResponse,
  CitationVerificationResponse,
  CitationVerificationRequest,
  QualityReport,
  // NEW: Format taxonomy types
  ResearchFormatListResponse,
  ResearchFormatDetail,
  ResearchLengthListResponse,
  ResearchAudienceListResponse,
  ResearchSkillListResponse,
} from '../types/api';


const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

let authToken: string | null = null;

const originalFetch = window.fetch;
const fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  const headers = new Headers(init?.headers);
  if (authToken) {
    headers.set('Authorization', `Bearer ${authToken}`);
  }
  return originalFetch(input, { ...init, headers });
};

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  setToken(token: string | null) {
    authToken = token;
  },

  async listWorkspaces(): Promise<{ id: string; name: string; created_at: string }[]> {
    const res = await fetch(`${BASE_URL}/workspaces`);
    return handleResponse<{ id: string; name: string; created_at: string }[]>(res);
  },

  async createWorkspace(name: string): Promise<{ id: string; name: string; created_at: string }> {
    const res = await fetch(`${BASE_URL}/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    return handleResponse<{ id: string; name: string; created_at: string }>(res);
  },
  /**
   * Fetch cache and circuit telemetry stats.
   */
  async getTelemetry(): Promise<TelemetryResponse> {
    const res = await fetch(`${BASE_URL}/api/telemetry`);
    return handleResponse<TelemetryResponse>(res);
  },

  /**
   * Fetch workspace-scoped app settings. API keys returned as booleans.
   */
  async getSettings(workspaceId: string): Promise<import('../types/api').SettingsResponse> {
    const res = await fetch(`${BASE_URL}/api/settings?workspace_id=${workspaceId}`);
    return handleResponse<import('../types/api').SettingsResponse>(res);
  },

  /**
   * Save app settings (PATCH — sends only changed fields).
   */
  async updateSettings(workspaceId: string, body: import('../types/api').AppSettingsPatch): Promise<void> {
    const res = await fetch(`${BASE_URL}/api/settings?workspace_id=${workspaceId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return handleResponse<void>(res);
  },

  /**
   * List all past research runs, newest first.
   */
  async listRuns(workspaceId: string): Promise<RunSummary[]> {
    const res = await fetch(`${BASE_URL}/runs?workspace_id=${workspaceId}`);
    return handleResponse<RunSummary[]>(res);
  },

  /**
   * Get the full ResearchResult details for a run.
   */
  async getRunDetails(runId: string): Promise<ResearchResult> {
    const res = await fetch(`${BASE_URL}/runs/${runId}`);
    return handleResponse<ResearchResult>(res);
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

  async createResearchRun(req: ResearchRequest): Promise<{ run_id: string }> {
    const res = await fetch(`${BASE_URL}/research/comprehensive`, {
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

  // ─── Format Taxonomy API (Slice 6) ─────────────────────────────────

  /** List all available research output formats. */
  async listResearchFormats(): Promise<ResearchFormatListResponse> {
    const res = await fetch(`${BASE_URL}/research/formats`);
    return handleResponse<ResearchFormatListResponse>(res);
  },

  /** Get detailed metadata for a specific research format. */
  async getResearchFormat(formatId: string): Promise<ResearchFormatDetail> {
    const res = await fetch(`${BASE_URL}/research/formats/${encodeURIComponent(formatId)}`);
    return handleResponse<ResearchFormatDetail>(res);
  },

  /** Get length options for a specific research format. */
  async getResearchFormatLengths(formatId: string): Promise<ResearchLengthListResponse> {
    const res = await fetch(`${BASE_URL}/research/formats/${encodeURIComponent(formatId)}/lengths`);
    return handleResponse<ResearchLengthListResponse>(res);
  },

  /** Get audience options for a specific research format. */
  async getResearchFormatAudiences(formatId: string): Promise<ResearchAudienceListResponse> {
    const res = await fetch(`${BASE_URL}/research/formats/${encodeURIComponent(formatId)}/audiences`);
    return handleResponse<ResearchAudienceListResponse>(res);
  },

  /** List all available research skills. */
  async listResearchSkills(): Promise<ResearchSkillListResponse> {
    const res = await fetch(`${BASE_URL}/research/skills`);
    return handleResponse<ResearchSkillListResponse>(res);
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

  // ──── GitNexus Code Architecture (DEPRECATED) ───────────────────────
  // Old endpoints (/gitnexus/repos, /gitnexus/graph, /gitnexus/analyze,
  // /gitnexus/status) removed — they caused LadybugDB lock contention
  // with `gitnexus serve`. Use the Web UI Bridge endpoints below instead.

  // ──── GitNexus Web UI Bridge (gitnexus serve) ─────────────────────

  /** Start `npx gitnexus serve` on port 4747 so the GitNexus web UI can connect. */
  async startGitnexusServe(): Promise<{
    status: string;
    port: number;
    pid: number;
    web_ui_url: string;
    message: string;
  }> {
    const res = await fetch(`${BASE_URL}/gitnexus/serve/start`, { method: 'POST' });
    return handleResponse(res);
  },

  /** Stop the running `npx gitnexus serve` process. */
  async stopGitnexusServe(): Promise<{ status: string; pid?: number; message?: string }> {
    const res = await fetch(`${BASE_URL}/gitnexus/serve/stop`, { method: 'POST' });
    return handleResponse(res);
  },

  /** Check if `npx gitnexus serve` is running and get its PID and port. */
  async getGitnexusServeStatus(): Promise<{
    running: boolean;
    pid: number | null;
    port: number;
    web_ui_url: string;
  }> {
    const res = await fetch(`${BASE_URL}/gitnexus/serve/status`);
    return handleResponse(res);
  },

  /**
   * Open a file in the local editor.
   */
  async openFile(path: string): Promise<{ status: string; message?: string }> {
    const res = await fetch(`${BASE_URL}/open-file`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
    return handleResponse<{ status: string; message?: string }>(res);
  },

  /**
   * Resynthesize research report excluding disabled domains with SSE streaming.
   *
   * Uses fetch + ReadableStream (not EventSource, since we need POST).
   * Returns an AbortController for cleanup.
   */
  resynthesizeRun(
    runId: string,
    disabledDomains: string[],
    onEvent: (event: ResearchEvent) => void,
    onDone: (data: Record<string, any>) => void,
    onError: (error: string) => void,
  ): AbortController {
    const controller = new AbortController();

    const run = async () => {
      try {
        const res = await fetch(`${BASE_URL}/runs/${runId}/resynthesize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ disabled_domains: disabledDomains }),
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
                if (currentEvent === 'error') {
                  onError(data.error || 'Unknown error');
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

  // ─── Notes ─────────────────────────────────────────────────────

  listNotes: async (workspaceId: string): Promise<NoteSummary[]> => {
    const res = await fetch(`${BASE_URL}/notes?workspace_id=${encodeURIComponent(workspaceId)}`);
    if (!res.ok) throw new Error(`Failed to list notes: ${res.status}`);
    return res.json();
  },

  searchNotes: async (workspaceId: string, query: string): Promise<NoteSearchResponse> => {
    const res = await fetch(`${BASE_URL}/notes/search?workspace_id=${encodeURIComponent(workspaceId)}&q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error(`Failed to search notes: ${res.status}`);
    return res.json();
  },

  getNote: async (noteId: string): Promise<Note> => {
    const res = await fetch(`${BASE_URL}/notes/${noteId}`);
    if (!res.ok) throw new Error(`Failed to get note: ${res.status}`);
    return res.json();
  },

  createNote: async (payload: { workspace_id: string; title: string; content?: string; tags?: string[]; source?: string }): Promise<Note> => {
    const res = await fetch(`${BASE_URL}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(body.detail || `Failed to create note: ${res.status}`);
    }
    return res.json();
  },

  updateNote: async (noteId: string, payload: { title?: string; content?: string; tags?: string[]; source?: string }): Promise<Note> => {
    const res = await fetch(`${BASE_URL}/notes/${noteId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(body.detail || `Failed to update note: ${res.status}`);
    }
    return res.json();
  },

  deleteNote: async (noteId: string): Promise<{ status: string; id: string }> => {
    const res = await fetch(`${BASE_URL}/notes/${noteId}`, { method: 'DELETE' });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(body.detail || `Failed to delete note: ${res.status}`);
    }
    return res.json();
  },

  deleteNotesBulk: async (ids: string[]): Promise<{ status: string; count: number }> => {
    const res = await fetch(`${BASE_URL}/notes/bulk-delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(body.detail || `Failed to bulk delete notes: ${res.status}`);
    }
    return res.json();
  },

  getNoteBacklinks: async (noteId: string): Promise<{ id: string; title: string; updated_at: string; snippet: string }[]> => {
    const res = await fetch(`${BASE_URL}/notes/${noteId}/backlinks`);
    if (!res.ok) throw new Error(`Failed to get backlinks: ${res.status}`);
    return res.json();
  },

  // ─── Documents / OpenKB ──────────────────────────────────────

  uploadDocument: async (workspaceId: string, file: File): Promise<{ document_id: string; filename: string; status: string; message: string }> => {
    const formData = new FormData();
    formData.append("workspace_id", workspaceId);
    formData.append("file", file);
    const res = await fetch(`${BASE_URL}/documents/upload`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`Failed to upload document: ${res.status}`);
    return res.json();
  },

  listDocuments: async (workspaceId: string): Promise<DocumentListResponse> => {
    const res = await fetch(`${BASE_URL}/documents?workspace_id=${encodeURIComponent(workspaceId)}`);
    if (!res.ok) throw new Error(`Failed to list documents: ${res.status}`);
    return res.json();
  },

  queryDocuments: async (workspaceId: string, question: string): Promise<DocumentQueryResponse> => {
    const formData = new FormData();
    formData.append("workspace_id", workspaceId);
    formData.append("question", question);
    const res = await fetch(`${BASE_URL}/documents/query`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`Failed to query documents: ${res.status}`);
    return res.json();
  },

  getWikiPage: async (workspaceId: string, pagePath: string): Promise<WikiPageResponse> => {
    const res = await fetch(`${BASE_URL}/documents/wiki/${encodeURIComponent(pagePath)}?workspace_id=${encodeURIComponent(workspaceId)}`);
    if (!res.ok) throw new Error(`Failed to get wiki page: ${res.status}`);
    return res.json();
  },

  getOpenKBStatus: async (workspaceId: string): Promise<OpenKBStatus> => {
    const res = await fetch(`${BASE_URL}/documents/status?workspace_id=${encodeURIComponent(workspaceId)}`);
    if (!res.ok) throw new Error(`Failed to get OpenKB status: ${res.status}`);
    return res.json();
  },

  createSkill: async (workspaceId: string, name: string, intent: string): Promise<SkillResponse> => {
    const formData = new FormData();
    formData.append("workspace_id", workspaceId);
    formData.append("name", name);
    formData.append("intent", intent);
    const res = await fetch(`${BASE_URL}/documents/skills`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`Failed to create skill: ${res.status}`);
    return res.json();
  },

  listSkills: async (workspaceId: string): Promise<SkillListResponse> => {
    const res = await fetch(`${BASE_URL}/documents/skills?workspace_id=${encodeURIComponent(workspaceId)}`);
    if (!res.ok) throw new Error(`Failed to list skills: ${res.status}`);
    return res.json();
  },

  validateSkill: async (workspaceId: string, skillName: string): Promise<{ valid: boolean; error?: string; files?: string[]; skill_name?: string }> => {
    const res = await fetch(`${BASE_URL}/documents/skills/${encodeURIComponent(skillName)}/validate?workspace_id=${encodeURIComponent(workspaceId)}`);
    if (!res.ok) throw new Error(`Failed to validate skill: ${res.status}`);
    return res.json();
  },

  evaluateSkill: async (workspaceId: string, skillName: string): Promise<{ coverage: number; concepts_matched?: number; total_concepts?: number; error?: string; skill_name?: string }> => {
    const res = await fetch(`${BASE_URL}/documents/skills/${encodeURIComponent(skillName)}/eval?workspace_id=${encodeURIComponent(workspaceId)}`);
    if (!res.ok) throw new Error(`Failed to evaluate skill: ${res.status}`);
    return res.json();
  },

  rollbackSkill: async (workspaceId: string, skillName: string): Promise<{ success: boolean; message?: string; error?: string }> => {
    const res = await fetch(`${BASE_URL}/documents/skills/${encodeURIComponent(skillName)}/rollback?workspace_id=${encodeURIComponent(workspaceId)}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`Failed to rollback skill: ${res.status}`);
    return res.json();
  },

  deleteDocument: async (workspaceId: string, docId: string): Promise<{ success: boolean; message: string }> => {
    const res = await fetch(`${BASE_URL}/documents/${encodeURIComponent(docId)}?workspace_id=${encodeURIComponent(workspaceId)}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error(`Failed to delete document: ${res.status}`);
    return res.json();
  },

  recompileDocuments: async (workspaceId: string): Promise<{ success: boolean; message: string }> => {
    const res = await fetch(`${BASE_URL}/documents/recompile?workspace_id=${encodeURIComponent(workspaceId)}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`Failed to recompile documents: ${res.status}`);
    return res.json();
  },

  downloadDocument: (workspaceId: string, docId: string): string => {
    return `${BASE_URL}/documents/${encodeURIComponent(docId)}/download?workspace_id=${encodeURIComponent(workspaceId)}`;
  },

  getDocumentStats: async (workspaceId: string): Promise<{
    workspace_id: string;
    document_count: number;
    concept_count: number;
    entity_count: number;
    summary_count: number;
    wiki_size_bytes: number;
  }> => {
    const res = await fetch(`${BASE_URL}/documents/stats?workspace_id=${encodeURIComponent(workspaceId)}`);
    if (!res.ok) throw new Error(`Failed to get document stats: ${res.status}`);
    return res.json();
  },

  seedNotes: async (workspaceId: string): Promise<{ success: boolean; message: string; created: number }> => {
    const formData = new FormData();
    formData.append("workspace_id", workspaceId);
    const res = await fetch(`${BASE_URL}/notes/seed`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(body.detail || `Failed to seed notes: ${res.status}`);
    }
    return res.json();
  },

  chatDocuments: async (workspaceId: string, message: string, sessionId?: string): Promise<{
    session_id: string;
    response: string;
    history: { role: string; content: string }[];
  }> => {
    const formData = new FormData();
    formData.append("workspace_id", workspaceId);
    formData.append("message", message);
    if (sessionId) formData.append("session_id", sessionId);
    const res = await fetch(`${BASE_URL}/documents/chat`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`Failed to chat: ${res.status}`);
    return res.json();
  },

  listChatSessions: async (workspaceId: string): Promise<{
    sessions: { session_id: string; message_count: number; last_message: string }[];
  }> => {
    const res = await fetch(`${BASE_URL}/documents/chat/sessions?workspace_id=${encodeURIComponent(workspaceId)}`);
    if (!res.ok) throw new Error(`Failed to list chat sessions: ${res.status}`);
    return res.json();
  },

  downloadWikiZip: (workspaceId: string): string => {
    return `${BASE_URL}/documents/wiki/download?workspace_id=${encodeURIComponent(workspaceId)}`;
  },

  verifyCitation: async (request: CitationVerificationRequest): Promise<CitationVerificationResponse> => {
    const res = await fetch(`${BASE_URL}/citations/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return handleResponse<CitationVerificationResponse>(res);
  },

  getQualityReport: async (runId: string): Promise<QualityReport> => {
    const res = await fetch(`${BASE_URL}/research/${runId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse<QualityReport>(res);
  },
};

// Named export aliases for components that import these directly
export const verifyCitation = api.verifyCitation;
export const getQualityReport = api.getQualityReport;
export const setAuthToken = (token: string | null) => api.setToken(token);
