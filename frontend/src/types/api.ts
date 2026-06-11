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
  provider?: string;  // LLM provider: 'openrouter' | 'groq'
  mode?: 'web' | 'github';
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
  provider?: string;  // LLM provider: 'openrouter' | 'groq'
  export_formats?: string[];
  mode?: 'web' | 'github';
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

export type ExportFormat =
  | 'markdown'
  | 'pdf'
  | 'docx'
  | 'xlsx'
  | 'mindmap_json'
  | 'knowledge_graph'
  | 'graph_html';

export type ExportFormatInfo = {
  format: ExportFormat;
  extension: string;
  cached: boolean;
};

// ─── Knowledge Graph (Graphify) ─────────────────────────────────────

export type KGProvenance = 'EXTRACTED' | 'INFERRED' | 'AMBIGUOUS';

export type KGNode = {
  id: string;
  label: string;
  type: string;           // 'function' | 'class' | 'concept' | 'paper' | 'diagram'
  community: number;      // Leiden community ID
  degree: number;         // Edge count — higher = more connected
  is_god_node: boolean;   // Top-N highest-degree nodes
  provenance: KGProvenance;
  confidence: number;     // 0–1, relevant for INFERRED edges
  summary?: string;
  file_path?: string;
};

export type KGEdge = {
  source: string;
  target: string;
  type: string;           // 'calls' | 'imports' | 'rationale_for' | 'semantically_similar_to'
  provenance: KGProvenance;
  confidence: number;
  label?: string;
};

export type KGCommunity = {
  id: number;
  label: string;
  node_count: number;
  keywords: string[];
  description?: string;
};

export type SurpriseEdge = {
  source: string;
  target: string;
  reason: string;         // Plain-English explanation of why this connection is surprising
  score: number;
};

export type KnowledgeGraph = {
  run_id: string;
  nodes: KGNode[];
  edges: KGEdge[];
  communities: KGCommunity[];
  god_nodes: string[];            // Node IDs of highest-degree nodes
  surprise_edges: SurpriseEdge[];
  built_at: string;
  graphify_version?: string;
  graph_html_available: boolean;
  corpus_stats: Record<string, number>;
  naive_token_cost: number;
  graph_token_cost: number;
  compression_ratio: number;
};

export type KGQueryRequest = {
  question: string;
  mode?: 'bfs' | 'dfs';
  budget?: number;
};

export type KGQueryResult = {
  answer: string;
  nodes_traversed: string[];
  token_cost: number;
  query_mode: string;
};

export type KGMcpStatus = {
  running: boolean;
  run_id: string;
  pid?: number;
};

export type KGAvailability = {
  run_id: string;
  knowledge_graph_available: boolean;
  graph_html_available: boolean;
};

export type OpenFileRequest = {
  path: string;
};


