import { useState, useEffect, useRef } from 'react';
import {
  Search,
  FileText,
  Brain,
  Check,
  AlertTriangle,
  RefreshCw,
  Filter,
  Pencil,
  ListChecks,
  Network,
  Lightbulb,
} from 'lucide-react';
import type { ResearchEvent } from '../../types/api';

type Props = {
  events: ResearchEvent[];
  isActive: boolean;
};

interface ScrapedPageInfo {
  url: string;
  title?: string;
  success: boolean;
  fetcher_used?: string;
  content_length?: number;
  original_status?: number;
  fallback_attempts?: string[];
  error?: string;
}

interface SearchResultInfo {
  url: string;
  title?: string;
  snippet?: string;
  score: number;
  relevance_score?: number;
  eval_rationale?: string;
}

interface CycleData {
  cycle: number;
  query?: string;
  search_results?: SearchResultInfo[];
  scraped_pages?: ScrapedPageInfo[];
  answerLength?: number;
  citationCount?: number;
  planUpdated?: boolean;
  confidenceScore?: number;
  confidenceReasoning?: string;
  needsMoreResearch?: boolean;
  progressPercent?: number;
  isReflecting?: boolean;
  isSearching?: boolean;
  isScraping?: boolean;
  isValidating?: boolean;
  isSynthesizing?: boolean;
}

const STATE_CONFIG: Record<
  string,
  { icon: React.ComponentType<{ size?: number; className?: string }>; color: string; label: string }
> = {
  initializing: { icon: Network, color: '#999', label: 'Initializing' },
  classifying_intent: { icon: Lightbulb, color: '#8b5cf6', label: 'Classifying Intent' },
  planning: { icon: ListChecks, color: '#8b5cf6', label: 'Creating Plan' },
  plan_ready: { icon: Check, color: '#7dac5a', label: 'Plan Ready' },
  decomposing: { icon: Brain, color: '#22d3ee', label: 'Decomposing Query' },
  searching: { icon: Search, color: '#3b82f6', label: 'Searching' },
  scraping: { icon: FileText, color: '#f97316', label: 'Scraping Pages' },
  validating: { icon: Filter, color: '#14b8a6', label: 'Validating Results' },
  synthesizing: { icon: Brain, color: '#6366f1', label: 'Synthesizing' },
  reflecting: { icon: Brain, color: '#a855f7', label: 'Reflecting' },
  retrying: { icon: RefreshCw, color: '#eab308', label: 'Retrying' },
  cycle_complete: { icon: Check, color: '#7dac5a', label: 'Cycle Complete' },
  generating_report: {
    icon: Pencil,
    color: '#ec4899',
    label: 'Writing Report',
  },
  complete: { icon: Check, color: '#7dac5a', label: 'Complete' },
  error: { icon: AlertTriangle, color: '#c45a5a', label: 'Error' },
};

export function ResearchProgress({ events, isActive }: Props) {
  const [currentCycle, setCurrentCycle] = useState(0);
  const [maxCycles, setMaxCycles] = useState(0);
  const [progressPercent, setProgressPercent] = useState(0);
  const [currentState, setCurrentState] = useState('initializing');
  const [cycles, setCycles] = useState<CycleData[]>([]);
  const [intentData, setIntentData] = useState<any>(null);
  const [thinkingText, setThinkingText] = useState('');
  const [scrapeProgress, setScrapeProgress] = useState<Record<string, any>>({});
  const [openCycles, setOpenCycles] = useState<Set<number>>(new Set());
  const [thinkingOpen, setThinkingOpen] = useState(true);
  const timelineEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const cycleMap: Record<number, CycleData> = {};
    let foundIntent = null;
    let thinking = '';
    const nextScrapeProgress: Record<string, any> = {};

    for (const ev of events) {
      if (ev.data?.max_cycles) setMaxCycles(ev.data.max_cycles);
      if (ev.data?.progress) setProgressPercent(ev.data.progress);
      setCurrentState(ev.event);

      if (ev.event === 'plan_ready' && ev.data?.intent) {
        foundIntent = ev.data.intent;
      }

      if (ev.event === 'thinking_chunk' && ev.data?.chunk) {
        thinking += ev.data.chunk;
      }

      if (ev.event === 'scrape_progress' && ev.data) {
        const { url, status, details, cycle } = ev.data;
        const existing = nextScrapeProgress[url] || { url, status, cycle };
        existing.status = status;
        if (details?.fetcher) existing.fetcher = details.fetcher;
        if (details?.content_length) existing.contentLength = details.content_length;
        if (details?.error) existing.error = details.error;
        nextScrapeProgress[url] = existing;
      }

      if (ev.data?.cycle) {
        const cNum = ev.data.cycle;
        setCurrentCycle(cNum);
        if (!cycleMap[cNum]) {
          cycleMap[cNum] = {
            cycle: cNum,
            search_results: [],
            scraped_pages: [],
          };
        }
        const c = cycleMap[cNum];

        if (ev.event === 'searching') {
          c.query = ev.data.query;
          c.isSearching = true;
          c.isScraping = false;
          c.isValidating = false;
          c.isSynthesizing = false;
          c.isReflecting = false;
        } else if (ev.event === 'scraping') {
          c.isSearching = false;
          c.isScraping = true;
          if (ev.data.pages) {
            c.scraped_pages = ev.data.pages;
          }
          if (ev.data.search_results) {
            c.search_results = ev.data.search_results;
          }
        } else if (ev.event === 'validating') {
          c.isScraping = false;
          c.isValidating = true;
        } else if (ev.event === 'synthesizing') {
          c.isValidating = false;
          c.isSynthesizing = true;
        } else if (ev.event === 'reflecting') {
          c.isSynthesizing = false;
          c.isReflecting = true;
        } else if (ev.event === 'cycle_complete') {
          c.isReflecting = false;
          c.answerLength = ev.data.answer_length;
          c.citationCount = ev.data.citation_count;
          c.planUpdated = ev.data.plan_updated;
        } else if (ev.event === 'confidence') {
          c.confidenceScore = ev.data.score;
          c.confidenceReasoning = ev.data.reasoning;
          c.needsMoreResearch = ev.data.needs_more_research;
        } else if (ev.event === 'progress') {
          c.progressPercent = ev.data.progress;
        }
      }
    }

    const sortedCycles = Object.values(cycleMap).sort((a, b) => a.cycle - b.cycle);
    setCycles(sortedCycles);
    if (foundIntent) {
      setIntentData(foundIntent);
    }
    setThinkingText(thinking);
    setScrapeProgress(nextScrapeProgress);
  }, [events]);

  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  const stateConfig = STATE_CONFIG[currentState] || STATE_CONFIG.initializing;

  // Filter non-cycle events for the top/bottom static timeline items
  const nonCycleEvents = events.filter((ev) =>
    ['planning', 'plan_ready', 'decomposing', 'generating_report', 'complete', 'error'].includes(ev.event)
  );

  return (
    <div className="flex flex-col gap-6">
      {/* ─── Status Header ─────────────────────────────────── */}
      <div className="liquid-glass p-6 rounded-xl">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {isActive ? (
              <div className="w-6 h-6 border-2 border-[#c8956c] border-t-transparent rounded-full animate-spin" />
            ) : (
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                style={{ backgroundColor: `${stateConfig.color}22` }}
              >
                <span style={{ color: stateConfig.color }}><stateConfig.icon size={20} /></span>
              </div>
            )}
            <div>
              <div className="text-lg font-semibold text-[#e0e0e0]" style={{ fontFamily: 'Fira Sans' }}>
                {stateConfig.label}
              </div>
              <div className="text-sm text-[#999]">
                {isActive ? 'Research in progress...' : 'Research completed'}
              </div>
            </div>
          </div>

          {maxCycles > 0 && (
            <div
              className="relative w-20 h-20 rounded-full flex items-center justify-center flex-shrink-0"
              style={{
                background: `conic-gradient(#c8956c ${maxCycles ? (currentCycle / maxCycles) * 100 : 0}%, transparent ${maxCycles ? (currentCycle / maxCycles) * 100 : 0}%)`,
              }}
            >
              <div className="absolute inset-[6px] bg-[#0a0a0a] rounded-full flex items-center justify-center">
                <span className="text-xs font-bold font-mono text-[#e0e0e0]">
                  {currentCycle}/{maxCycles}
                </span>
              </div>
            </div>
          )}
        </div>

        {maxCycles > 0 && (
          <div className="h-2 bg-[#333] rounded-full overflow-hidden mt-4">
            <div
              className="h-full bg-[#c8956c] rounded-full transition-all"
              style={{ width: `${maxCycles ? (currentCycle / maxCycles) * 100 : 0}%` }}
            />
          </div>
        )}

        {progressPercent > 0 && (
          <div className="mt-1 flex items-center justify-between">
            <span className="text-xs text-[#999]">Research coverage</span>
            <span
              className="px-2 py-0.5 text-[10px] rounded-full font-mono font-medium"
              style={{
                backgroundColor: progressPercent >= 80 ? '#7dac5a' : progressPercent >= 50 ? '#eab308' : '#f97316',
                color: '#000',
              }}
            >
              {progressPercent}%
            </span>
          </div>
        )}
      </div>

      {/* ─── Intent classification Details (If Available) ─── */}
      {intentData && (
        <div className="liquid-glass p-6 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-6 h-6 rounded-full bg-[#8b5cf6]/15 flex items-center justify-center flex-shrink-0">
              <Lightbulb size={16} className="text-[#8b5cf6]" />
            </div>
            <h5 className="text-base font-bold text-[#e0e0e0]" style={{ fontFamily: 'Fira Sans' }}>
              Query Intent Classified
            </h5>
            <span
              className="px-2 py-0.5 text-[10px] rounded-full font-medium"
              style={{
                backgroundColor:
                  intentData.category === 'academic'
                    ? '#8b5cf6'
                    : intentData.category === 'news'
                    ? '#14b8a6'
                    : intentData.category === 'technical'
                    ? '#3b82f6'
                    : '#999',
                color: '#000',
              }}
            >
              {intentData.category.toUpperCase()}
            </span>
          </div>
          <p className="text-sm text-[#999] mb-4">{intentData.rationale}</p>
          <div className="flex flex-wrap gap-6">
            {intentData.target_domains?.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-[#999] block mb-1">🎯 Target Domains:</span>
                <div className="flex flex-wrap gap-1">
                  {intentData.target_domains.map((d: string) => (
                    <span
                      key={d}
                      className="px-2 py-0.5 text-[10px] rounded-full border border-[#7dac5a] text-[#7dac5a]"
                    >
                      {d}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {intentData.avoid_domains?.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-[#999] block mb-1">🚫 Avoid Domains:</span>
                <div className="flex flex-wrap gap-1">
                  {intentData.avoid_domains.map((d: string) => (
                    <span
                      key={d}
                      className="px-2 py-0.5 text-[10px] rounded-full border border-[#c45a5a] text-[#c45a5a]"
                    >
                      {d}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── Thinking Process ────────────────────────────────── */}
      {thinkingText && (
        <div className="liquid-glass p-6 rounded-xl">
          <button
            className="flex items-center gap-2 w-full text-left px-3 pb-3 hover:bg-transparent bg-transparent transition-colors"
            onClick={() => setThinkingOpen(!thinkingOpen)}
          >
            <Brain size={18} className="text-[#c8956c]" />
            <div className="flex items-center justify-between flex-1">
              <span className="text-sm font-semibold text-[#e0e0e0]" style={{ fontFamily: 'Fira Sans' }}>
                Thinking Process
              </span>
              {isActive && currentState !== 'complete' && (
                <div className="w-4 h-4 border-2 border-[#c8956c] border-t-transparent rounded-full animate-spin" />
              )}
            </div>
          </button>
          {thinkingOpen && (
            <div className="border border-[#333] rounded-lg overflow-hidden">
              {/* Terminal Header */}
              <div className="bg-[#0a0a0a] px-3 py-2 border-b border-[#333] flex items-center justify-between">
                <div className="flex gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#ef4444] inline-block" />
                  <span className="w-2.5 h-2.5 rounded-full bg-[#f59e0b] inline-block" />
                  <span className="w-2.5 h-2.5 rounded-full bg-[#10b981] inline-block" />
                </div>
                <span className="text-xs font-mono text-[#999]">research_agent --verbose</span>
                <span className="w-[30px]" />
              </div>
              <div
                className={`font-mono p-4 overflow-y-auto whitespace-pre-wrap ${
                  isActive && currentState !== 'complete' ? 'blink-cursor' : ''
                }`}
                style={{
                  maxHeight: '300px',
                  backgroundColor: '#000000',
                  color: '#c8956c',
                  fontSize: '0.85rem',
                }}
              >
                {thinkingText}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ─── Scraper Queue Dashboard ─────────────────────────── */}
      {Object.keys(scrapeProgress).length > 0 && (
        <div className="liquid-glass p-6 rounded-xl">
          <h5
            className="text-base font-bold mb-2"
            style={{ fontFamily: 'Fira Sans', fontWeight: 600 }}
          >
            Scraper Queue Dashboard
          </h5>
          <p className="text-xs text-[#999] mb-4">
            Real-time status of pages being fetched and analyzed
          </p>
          <div className="overflow-x-auto">
            <table className="telemetry-table w-full">
              <thead>
                <tr>
                  <th className="w-[60px]">Cycle</th>
                  <th>Domain</th>
                  <th>Status</th>
                  <th>Fetcher</th>
                  <th className="w-[90px]">Size</th>
                </tr>
              </thead>
              <tbody>
                {Object.values(scrapeProgress).map((p, idx) => {
                  let domain = p.url;
                  try {
                    domain = new URL(p.url).hostname;
                  } catch {
                    // ignore
                  }
                  const isActiveRow = p.status === 'TRYING_TIER' || p.status === 'START';
                  let statusColor = '#999';
                  if (p.status === 'COMPLETE' || p.status === 'CACHE_HIT') statusColor = '#c8956c';
                  else if (p.status === 'FAILED' || p.status === 'SKIPPED_CIRCUIT') statusColor = '#c45a5a';
                  else if (p.status === 'TRYING_TIER' || p.status === 'START') statusColor = '#eab308';

                  return (
                    <tr key={idx} className={isActiveRow ? 'active-row' : ''}>
                      <td className="text-center">
                        <span className="px-2 py-0.5 text-[10px] rounded-full font-mono bg-[#555] text-[#000]">
                          {p.cycle}
                        </span>
                      </td>
                      <td>
                        <a
                          href={p.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs truncate inline-block max-w-[250px] text-[#e0e0e0] hover:text-[#d4a574] transition-colors"
                        >
                          {domain}
                        </a>
                      </td>
                      <td>
                        <span
                          className="px-2 py-0.5 text-[10px] rounded-full font-mono font-medium"
                          style={{ backgroundColor: statusColor, color: '#000' }}
                        >
                          {p.status}
                        </span>
                      </td>
                      <td>
                        <span className="text-xs font-mono text-[#999]">{p.fetcher || '-'}</span>
                      </td>
                      <td>
                        <span className="text-xs font-mono text-[#999]">
                          {p.contentLength !== undefined
                            ? `${(p.contentLength / 1024).toFixed(1)} KB`
                            : '-'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ─── Event Timeline ────────────────────────────────── */}
      <div className="liquid-glass p-6 rounded-xl">
        <h5
          className="text-base font-bold mb-4"
          style={{ fontFamily: 'Fira Sans', fontWeight: 600 }}
        >
          Research Timeline
        </h5>

        <div className="relative">
          <div className="absolute left-3.5 top-0 bottom-0 w-0.5 bg-[#333]" />

          {/* Static Pre-run Steps */}
          {nonCycleEvents
            .filter((ev) => ['planning', 'plan_ready', 'decomposing'].includes(ev.event))
            .map((ev, idx) => {
              const cfg = STATE_CONFIG[ev.event] || STATE_CONFIG.initializing;
              return (
                <div key={`pre-${idx}`} className="relative flex gap-4 mb-6">
                  <div
                    className="relative z-10 w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: cfg.color }}
                  >
                    <cfg.icon size={14} className="text-[#000]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-[#e0e0e0]">{cfg.label}</div>
                    {ev.event === 'plan_ready' && (
                      <div className="flex flex-col gap-1 mt-1">
                        {Array.isArray(ev.data.sub_queries) && ev.data.sub_queries.length > 0 && (
                          <>
                            <span className="text-xs text-[#999]">Sub-queries:</span>
                            <div className="flex flex-wrap gap-1">
                              {(ev.data.sub_queries as string[]).map((q, i) => (
                                <span
                                  key={i}
                                  className="px-2 py-0.5 text-[10px] rounded-full bg-[#22d3ee]/10 text-[#22d3ee]"
                                >
                                  {q.length > 50 ? q.slice(0, 50) + '…' : q}
                                </span>
                              ))}
                            </div>
                          </>
                        )}
                        <span className="text-xs text-[#999]">
                          📋 {ev.data.step_count ?? 0} research steps planned
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

          {/* Dynamic Cycle-Grouped Steps */}
          {cycles.map((c) => {
            const isFinished = c.answerLength !== undefined;
            const CycleIcon = isFinished ? Check : Search;
            const color = isFinished ? '#c8956c' : '#3b82f6';

            return (
              <div key={`cycle-${c.cycle}`} className="relative flex gap-4 mb-6">
                <div
                  className="relative z-10 w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{ backgroundColor: color, opacity: isFinished ? 1 : 0.3 }}
                >
                  {c.isScraping ? (
                    <FileText size={14} className="text-[#000]" />
                  ) : (
                    <CycleIcon size={14} className="text-[#000]" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className="text-sm font-semibold text-[#e0e0e0]"
                      style={{ fontFamily: 'Fira Sans' }}
                    >
                      Cycle {c.cycle}
                    </span>
                    {c.isSearching && (
                      <span className="px-2 py-0.5 text-[10px] rounded-full bg-[#3b82f6]/15 text-[#3b82f6]">
                        Searching
                      </span>
                    )}
                    {c.isScraping && (
                      <span className="px-2 py-0.5 text-[10px] rounded-full bg-[#f97316]/15 text-[#f97316]">
                        Scraping
                      </span>
                    )}
                    {c.isValidating && (
                      <span className="px-2 py-0.5 text-[10px] rounded-full bg-[#14b8a6]/15 text-[#14b8a6]">
                        Filtering
                      </span>
                    )}
                    {c.isSynthesizing && (
                      <span className="px-2 py-0.5 text-[10px] rounded-full bg-[#6366f1]/15 text-[#6366f1]">
                        Synthesizing
                      </span>
                    )}
                    {c.isReflecting && (
                      <span className="px-2 py-0.5 text-[10px] rounded-full bg-[#a855f7]/15 text-[#a855f7]">
                        Reflecting
                      </span>
                    )}
                    {isFinished && (
                      <span className="px-2 py-0.5 text-[10px] rounded-full bg-[#c8956c] text-[#000]">
                        Complete
                      </span>
                    )}
                  </div>
                  <button
                    className="mt-2 text-xs text-[#999] hover:text-[#e0e0e0] transition-colors text-left w-full"
                    onClick={() => {
                      const next = new Set(openCycles);
                      if (next.has(c.cycle)) next.delete(c.cycle);
                      else next.add(c.cycle);
                      setOpenCycles(next);
                    }}
                  >
                    {c.query ? `Query: "${c.query.slice(0, 60)}..."` : 'Details & Scraped Contents'}
                  </button>
                  {openCycles.has(c.cycle) && (
                    <div className="mt-2 flex flex-col gap-3">
                      {c.query && (
                        <div>
                          <span
                            className="text-xs font-semibold text-[#999] block mb-1"
                            style={{ fontFamily: 'Fira Sans' }}
                          >
                            🔍 Search Query:
                          </span>
                          <div className="p-2 rounded-lg bg-[#0a0a0a] border border-[#333] font-mono text-[#c8956c] text-xs whitespace-pre-wrap">
                            {c.query}
                          </div>
                        </div>
                      )}

                      {/* Pointwise AutoEval Search relevance List */}
                      {c.search_results && c.search_results.length > 0 && (
                        <div>
                          <span
                            className="text-xs font-semibold text-[#999] block mb-1"
                            style={{ fontFamily: 'Fira Sans' }}
                          >
                            🎯 snippet AutoEval Relevance Scores:
                          </span>
                          <div className="flex flex-col gap-1.5">
                            {c.search_results.map((r, i) => {
                              const score = r.relevance_score ?? 1.0;
                              const passed = score >= 0.7;
                              return (
                                <div
                                  key={i}
                                  className="p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]"
                                >
                                  <div className="flex items-start justify-between gap-2">
                                    <div className="flex flex-col gap-0.5 flex-1 min-w-0">
                                      <a
                                        href={r.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs font-medium truncate text-[#7dac5a] hover:text-[#d4a574] transition-colors"
                                      >
                                        {r.title || r.url}
                                      </a>
                                      <span className="text-[10px] text-[#999] line-clamp-2">
                                        {r.snippet}
                                      </span>
                                      {r.eval_rationale && (
                                        <span className="text-[10px] italic text-[#999]">
                                          Judge: {r.eval_rationale}
                                        </span>
                                      )}
                                    </div>
                                    <span
                                      className="px-2 py-0.5 text-[10px] rounded-full font-mono font-medium flex-shrink-0"
                                      style={{
                                        backgroundColor: passed ? '#c8956c' : '#c45a5a',
                                        color: '#000',
                                      }}
                                    >
                                      {score.toFixed(2)}
                                    </span>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Inline list of scraped pages with fallback diagnostics */}
                      {c.scraped_pages && c.scraped_pages.length > 0 && (
                        <div>
                          <span
                            className="text-xs font-semibold text-[#999] block mb-1"
                            style={{ fontFamily: 'Fira Sans' }}
                          >
                            📄 Scraped Content Fallbacks & Status:
                          </span>
                          <div className="flex flex-col gap-1">
                            {c.scraped_pages.map((p, i) => {
                              const fetcherColor =
                                p.fetcher_used === 'async_fetcher'
                                  ? '#7dac5a'
                                  : p.fetcher_used === 'dynamic_fetcher'
                                  ? '#f97316'
                                  : '#c8956c';
                              const fetcherLabel =
                                p.fetcher_used === 'async_fetcher'
                                  ? 'curl_cffi'
                                  : p.fetcher_used === 'dynamic_fetcher'
                                  ? 'Playwright'
                                  : 'Camoufox Stealth';

                              return (
                                <div
                                  key={i}
                                  className="p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]"
                                >
                                  <div className="flex items-start justify-between gap-2">
                                    <div className="flex flex-col gap-0.5 flex-1 min-w-0">
                                      <a
                                        href={p.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs font-medium truncate text-[#7dac5a] hover:text-[#d4a574] transition-colors"
                                      >
                                        {p.title || p.url}
                                      </a>
                                      {p.fallback_attempts && p.fallback_attempts.length > 1 && (
                                        <div className="flex items-center gap-1">
                                          <div className="w-4 h-4 rounded-full bg-[#eab308]/15 flex items-center justify-center flex-shrink-0">
                                            <RefreshCw size={10} className="text-[#eab308]" />
                                          </div>
                                          <span className="text-[10px] text-[#eab308] font-medium">
                                            Fell back: {p.fallback_attempts.join(' → ')}
                                          </span>
                                        </div>
                                      )}
                                      {!p.success && p.error && (
                                        <div className="flex items-center gap-1">
                                          <div className="w-4 h-4 rounded-full bg-[#c45a5a]/15 flex items-center justify-center flex-shrink-0">
                                            <AlertTriangle size={10} className="text-[#c45a5a]" />
                                          </div>
                                          <span className="text-[10px] text-[#c45a5a] font-medium">
                                            Failed: {p.error}
                                          </span>
                                        </div>
                                      )}
                                    </div>
                                    <div className="flex items-center gap-1 flex-shrink-0">
                                      <span
                                        className="px-2 py-0.5 text-[10px] rounded-full font-mono font-medium"
                                        style={{
                                          backgroundColor: p.success ? '#7dac5a' : '#c45a5a',
                                          color: '#000',
                                        }}
                                      >
                                        {p.success ? `200` : `ERR`}
                                      </span>
                                      {p.success && (
                                        <span
                                          className="px-2 py-0.5 text-[10px] rounded-full font-mono font-medium"
                                          style={{
                                            backgroundColor: `${fetcherColor}22`,
                                            color: fetcherColor,
                                          }}
                                        >
                                          {fetcherLabel}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Synthesis statistics & Confidence */}
                      {isFinished && (
                        <>
                          <div className="border-t border-[#333] my-2" />
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-0.5 text-[10px] rounded-full font-mono font-medium bg-[#3b82f6] text-[#000]">
                                {c.answerLength || 0} chars
                              </span>
                              <span className="px-2 py-0.5 text-[10px] rounded-full font-mono font-medium bg-[#c8956c] text-[#000]">
                                {c.citationCount || 0} citations
                              </span>
                              {c.planUpdated && (
                                <span className="px-2 py-0.5 text-[10px] rounded-full font-mono font-medium bg-[#8b5cf6] text-[#000]">
                                  Plan updated
                                </span>
                              )}
                            </div>

                            {c.confidenceScore !== undefined && (
                              <div className="relative group inline-flex">
                                <span
                                  className="px-2 py-0.5 text-[10px] rounded-full font-mono font-medium"
                                  style={{
                                    backgroundColor:
                                      c.confidenceScore >= 0.7
                                        ? '#7dac5a'
                                        : c.confidenceScore >= 0.4
                                        ? '#eab308'
                                        : '#c45a5a',
                                    color: '#000',
                                  }}
                                >
                                  Confidence: {Math.round(c.confidenceScore * 100)}%
                                </span>
                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 rounded-lg bg-[#1a1a1a] border border-[#333] text-xs text-[#999] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                                  {c.confidenceReasoning || ''}
                                </div>
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Static Post-run Steps */}
          {nonCycleEvents
            .filter((ev) => ['generating_report', 'complete', 'error'].includes(ev.event))
            .map((ev, idx) => {
              const cfg = STATE_CONFIG[ev.event] || STATE_CONFIG.initializing;
              return (
                <div key={`post-${idx}`} className="relative flex gap-4 mb-6">
                  <div
                    className="relative z-10 w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: cfg.color }}
                  >
                    <cfg.icon size={14} className="text-[#000]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-[#e0e0e0]">{cfg.label}</div>
                    {ev.event === 'complete' && (
                      <div className="flex items-center gap-2 mt-1">
                        <span className="px-2 py-0.5 text-[10px] rounded-full bg-[#7dac5a] text-[#000] font-mono">
                          {ev.data.total_cycles || 0} cycles
                        </span>
                        <span className="px-2 py-0.5 text-[10px] rounded-full bg-[#3b82f6] text-[#000] font-mono">
                          {ev.data.total_citations || 0} citations
                        </span>
                        {ev.data.duration_seconds && (
                          <span className="px-2 py-0.5 text-[10px] rounded-full bg-[#555]/15 text-[#999] font-mono">
                            {Math.round(ev.data.duration_seconds)}s
                          </span>
                        )}
                      </div>
                    )}
                    {ev.event === 'error' && (
                      <div className="mt-1 p-2 rounded-lg bg-[#c45a5a]/10 border border-[#c45a5a]/20 text-xs text-[#c45a5a]">
                        {ev.data.error || 'Unknown error'}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
        </div>

        <div ref={timelineEndRef} />
      </div>
    </div>
  );
}
