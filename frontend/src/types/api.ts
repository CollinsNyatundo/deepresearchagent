// ==========================================
// MANDATORY INTEGRITY WARNING
// DO NOT CHEAT. All implementations must be genuine.
// - DO NOT hardcode test results, expected outputs, or verification strings.
// - DO NOT create dummy or facade implementations.
// - Every implementation must maintain real state and produce real behavior.
// ==========================================

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
  status?: string;
  progress?: number;
  workspace_id?: string;
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
  workspace_id?: string;
  run_id?: string;
  // NEW: Format taxonomy fields
  format?: string;  // 'academic' | 'business' | 'technical' | 'product' | 'literature' | 'data'
  length?: string;  // format-specific length
  audience?: string;  // 'researcher' | 'executive' | 'cto' | 'pm' | etc.
  options?: Record<string, any>;  // format-specific options
  export_format?: string;  // 'markdown' | 'pdf' | 'docx' | 'latex'
  skills?: string[];  // override auto-resolved skills
};

// ─── SSE Streaming Events (Phase 2) ────────────────────────────────

export type ResearchState =
  | 'initializing'
  | 'classifying_intent'
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
  run_id?: string;
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
  workspace_id?: string;
  run_id?: string;
  // NEW: Format taxonomy fields
  format?: string;
  length?: string;
  audience?: string;
  options?: Record<string, any>;
  export_format?: string;
  skills?: string[];
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

export type SimilarityRequest = {
  query_embedding: number[];
  match_threshold: number;
  match_count: number;
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


// ─── Format Taxonomy Types (Slice 6) ─────────────────────────────────

export type ResearchFormat = {
  id: string;
  name: string;
  description: string;
  icon: string;
  length_count: number;
  audience_count: number;
};

export type ResearchFormatListResponse = {
  formats: ResearchFormat[];
};

export type ResearchFormatDetail = {
  id: string;
  name: string;
  description: string;
  icon: string;
  lengths: string[];
  audiences: string[];
  word_counts: Record<string, [number, number]>;
};

export type ResearchLengthOption = {
  id: string;
  name: string;
  word_count_min: number;
  word_count_max: number;
};

export type ResearchLengthListResponse = {
  lengths: ResearchLengthOption[];
};

export type ResearchAudienceOption = {
  id: string;
  name: string;
  description: string;
};

export type ResearchAudienceListResponse = {
  audiences: ResearchAudienceOption[];
};

export type ResearchSkill = {
  id: string;
  name: string;
  category: string;
  description: string;
};

export type ResearchSkillListResponse = {
  skills: ResearchSkill[];
};

export type QueryIntentCategory = 'academic' | 'news' | 'technical' | 'general';

export type QueryIntent = {
  category: QueryIntentCategory;
  rationale: string;
  target_domains: string[];
  avoid_domains: string[];
  steps_override?: string[];
  sub_queries?: string[];
};

export type RelevanceEvaluation = {
  score: number;
  rationale: string;
};


// ─── Research Result and Q&A Trace Types ──────────────────────────────

export type SearchQuery = {
  query: string;
  rationale?: string;
};

export type SearchQueryBatch = {
  queries: SearchQuery[];
};


export type SearchResult = {
  url: string;
  title?: string;
  snippet?: string;
  score?: number;
  relevance_score?: number;
  eval_rationale?: string;
  provider?: string;
};

export type ScrapedPage = {
  url: string;
  title?: string;
  content: string;
  status_code?: number;
  content_length: number;
  success: boolean;
  error?: string;
  fetcher_used?: string;
  original_status?: number;
  fallback_attempts?: string[];
};

export type Citation = {
  id: string;
  url: string;
  title?: string;
  domain?: string;
  accessed_at?: string;
  snippet?: string;
};

export type SearchAnswer = {
  answer: string;
  citations?: Citation[];
};

export type ResearchPlan = {
  steps: string[];
};

export type ResearchPlanReflection = {
  should_update: boolean;
  updates?: string;
};

export type ResearchStep = {
  cycle: number;
  query: SearchQuery;
  search_results?: SearchResult[];
  scraped_pages?: ScrapedPage[];
  answer: SearchAnswer;
  reflection?: ResearchPlanReflection;
  plan_updated?: boolean;
  progress?: number;
  timestamp?: string;
  needs_more_research?: boolean;
  confidence_score?: number;
};

export type ResearchResult = {
  run_id: string;
  query: string;
  model_used: string;
  plan: ResearchPlan;
  final_plan: ResearchPlan;
  steps: ResearchStep[];
  report: string;
  citations: Citation[];
  progress: number;
  started_at: string;
  completed_at: string;
  errors?: string[];
  workspace_id?: string;
  status?: string;
};


export type TelemetryResponse = {
  total_cached_queries: number;
  total_scraped_pages: number;
  active_circuit_breakers: string[];
  scraper_success_rate: number;
};

export type ResynthesizeRequest = {
  disabled_domains: string[];
  model?: string;
  provider?: string;
};

export type Workspace = {
  id: string;
  name: string;
  created_at: string;
};

// ─── Notes ───────────────────────────────────────────────────────

export type NoteSummary = {
  id: string;
  title: string;
  workspace_id: string;
  created_at: string;
  updated_at: string;
};

export type Note = {
  id: string;
  workspace_id: string;
  user_id: string;
  title: string;
  content: string;
  tags: string[];
  source: string | null;
  created_at: string;
  updated_at: string;
  outgoing_links: string[];
  backlink_count: number;
};

export type NoteSearchResponse = {
  notes: NoteSummary[];
  query: string;
  total: number;
};

// ─── Documents / OpenKB ──────────────────────────────────────────

export type Document = {
  id: string;
  workspace_id: string;
  user_id: string;
  filename: string;
  file_path: string;
  file_size: number;
  mime_type: string;
  status: string;
  page_count: number | null;
  indexed_at: string | null;
  created_at: string;
};

export type WikiPage = {
  path: string;
  title: string;
  type: string;
};

export type DocumentListResponse = {
  documents: Document[];
  wiki_pages: WikiPage[];
  wiki_status: string;
};

export type DocumentQueryResponse = {
  answer: string;
  workspace_id: string;
  question: string;
};

export type OpenKBStatus = {
  workspace_id: string;
  status: string;
};

export type SkillResponse = {
  skill_name: string;
  workspace_id: string;
  result: string;
};

export type SkillListResponse = {
  workspace_id: string;
  skills: string[];
};

export type WikiPageResponse = {
  path: string;
  content: string;
};

export type Backlink = {
  id: string;
  title: string;
  updated_at: string;
  snippet: string;
};

// ─── Citation Verification (Track A) ──────────────────────────────

export type CitationStatus = 'verified' | 'unverified' | 'failed';

export type VerificationResult = {
  status: CitationStatus;
  found: boolean;
  title: string;
  authors: string[];
  year: number | null;
  doi: string;
  url: string;
  confidence: number;
  sources: number;
};

export type CitationVerificationRequest = {
  citation_text: string;
};

export type CitationVerificationResponse = {
  status: CitationStatus;
  found: boolean;
  title: string;
  authors: string[];
  year: number | null;
  doi: string;
  url: string;
  confidence: number;
  sources: number;
};

// ─── Quality Review (Track B) ─────────────────────────────────────

export type QualityReport = {
  confidence_score: number;
  citation_verification_rate: number;
  source_diversity_score: number;
  completeness_score: number;
  coherence_score: number;
  improvement_suggestions: string[];
  overall_score: number;
};

export type QualityReviewRequest = {
  report: string;
  sources: { url: string; title: string }[];
};






