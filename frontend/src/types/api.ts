/* TypeScript types mirroring backend Pydantic models — source of truth: models.py */

// ─── Core Types ─────────────────────────────────────────────────────

export type CitationRef = {
  id: string;
  url: string;
  title?: string;
  domain?: string;
  snippet?: string;
};

export type MindmapNode = {
  id: string;
  label: string;
  type: 'root' | 'section' | 'detail';
  level: number;
  summary?: string;
  citations?: (CitationRef | string)[];
};

export type MindmapEdge = {
  source: string;
  target: string;
  label?: string;
};

export type MindmapGraph = {
  run_id: string;
  nodes: MindmapNode[];
  edges: MindmapEdge[];
};

export type NodeExpansion = {
  new_nodes: MindmapNode[];
  new_edges: MindmapEdge[];
};

export type RunSummary = {
  id: string;
  query: string;
  created_at: string;
  model_used?: string;
};

export type ResearchRequest = {
  query: string;
  model?: string;
  depth?: number;
  max_pages?: number;
  enable_crossover?: boolean;
  search_provider?: string;
};

// ─── SSE Streaming Events (Phase 2) ────────────────────────────────

export type ResearchState =
  | 'initializing'
  | 'planning'
  | 'plan_ready'
  | 'decomposing'
  | 'searching'
  | 'scraping'
  | 'validating'
  | 'synthesizing'
  | 'reflecting'
  | 'retrying'
  | 'cycle_complete'
  | 'generating_report'
  | 'complete'
  | 'error';

export type ResearchEvent = {
  event: ResearchState | string;
  data: Record<string, any>;
  timestamp?: string;
};

// ─── Interactive Plan Review (Phase 4) ──────────────────────────────

export type PlanPreview = {
  plan: { steps: string[] };
  sub_queries: string[];
  estimated_cycles: number;
  estimated_duration_minutes: number;
  output_formats: string[];
};

export type PlanApproval = {
  query: string;
  plan: { steps: string[] };
  sub_queries: string[];
  model?: string;
  depth?: number;
  max_pages?: number;
  enable_crossover?: boolean;
  search_provider?: string;
  export_formats?: string[];
};

// ─── Protocol-H Patterns (Phase 6) ─────────────────────────────────

export type ConfidenceScore = {
  score: number;
  reasoning: string;
  needs_more_research: boolean;
};

export type RetryInfo = {
  error: string;
  corrected_query?: string;
  reasoning?: string;
};

// ─── Export (Phase 5) ───────────────────────────────────────────────

export type ExportFormat = 'markdown' | 'pdf' | 'docx' | 'xlsx' | 'mindmap_json';

export type ExportFormatInfo = {
  format: ExportFormat;
  extension: string;
  cached: boolean;
};
