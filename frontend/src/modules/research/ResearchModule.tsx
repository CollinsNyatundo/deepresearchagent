import { useState, useCallback, useRef, useEffect } from 'react'
import { toast } from 'sonner'
import { z } from 'zod'
import { Plus, FlaskConical, ListChecks, Download, Quote } from 'lucide-react'

import { RunList } from '../../components/runs/RunList'
import { ReportView } from '../../components/views/ReportView'
import { CitationsView } from '../../components/views/CitationsView'
import { GitNexusWebView } from '../../components/code-arch/GitNexusWebView'
import { ResearchProgress } from '../../components/views/ResearchProgress'
import { PlanReview } from '../../components/views/PlanReview'
import { ExportPanel } from '../../components/views/ExportPanel'
import { TerminalDemo } from '../../components/landing/TerminalDemo'
import { api } from '../../api/client'
import type { ResearchEvent, PlanPreview, TelemetryResponse } from '../../types/api'
import { useAuth } from '../../lib/authContext'
import { WorkspaceSelector } from '../../components/Auth/WorkspaceSelector'
import Layout from '../../components/layout/Layout'
import { cn } from '../../lib/utils'
import { TokenCounter } from '../../components/TokenCounter'

const PRESETS = [
  { label: '⚡ Superconductivity', query: 'What are the latest breakthroughs in high-temperature superconductors?', provider: 'openrouter', model: 'nvidia/nemotron-3-super-120b-a12b:free', depth: 3, mode: 'web' },
  { label: '🦙 Llama Spec', query: 'Analyze Llama 3.3 70B performance compared to Claude 3.5 Sonnet', provider: 'groq', model: 'llama-3.3-70b-versatile', depth: 2, mode: 'web' },
  { label: '📘 TS Decorators', query: 'Explain TypeScript 5.0 decorators and provide comparison to stage 2 decorators', provider: 'openrouter', model: 'qwen/qwen3-235b-a22b:free', depth: 1, mode: 'web' },
]

const researchSchema = z.object({
  query: z.string().min(3, 'Query must be at least 3 characters'),
  model: z.string().min(1, 'Model is required'),
  depth: z.number().min(1).max(5),
  mode: z.enum(['web', 'github']),
  provider: z.enum(['openrouter', 'groq']),
})



type AppState = 'idle' | 'plan_loading' | 'plan_review' | 'streaming' | 'results'

export default function ResearchModule() {
  const { user, signOut } = useAuth()
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null)
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<string>('citations')
  const [refreshKey, setRefreshKey] = useState(0)

  const [globalView, setGlobalView] = useState<'research' | 'code-arch'>('research')
  const [appState, setAppState] = useState<AppState>('idle')

  const [query, setQuery] = useState('')
  const [model, setModel] = useState('nvidia/nemotron-3-super-120b-a12b:free')
  const [provider, setProvider] = useState<'openrouter' | 'groq'>('openrouter')
  const [depth, setDepth] = useState(5)
  const [mode, setMode] = useState<'web' | 'github'>('web')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [planPreview, setPlanPreview] = useState<PlanPreview | null>(null)
  const [planQuery, setPlanQuery] = useState('')

  const [streamEvents, setStreamEvents] = useState<ResearchEvent[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null)

  const handleProviderChange = (val: 'openrouter' | 'groq') => {
    setProvider(val)
    if (val === 'groq') {
      setModel('llama-3.3-70b-versatile')
    } else {
      setModel('nvidia/nemotron-3-super-120b-a12b:free')
    }
  }

  const fetchTelemetry = useCallback(async () => {
    try { setTelemetry(await api.getTelemetry()) }
    catch (err) { console.error('Telemetry failed:', err) }
  }, [])

  useEffect(() => {
    if (appState === 'idle' && !selectedRunId) fetchTelemetry()
  }, [appState, selectedRunId, fetchTelemetry])

  const handleGeneratePlan = useCallback(async () => {
    const validation = researchSchema.safeParse({ query, model, depth, mode, provider })
    if (!validation.success) {
      toast.error(validation.error.issues[0].message)
      return
    }
    if (!selectedWorkspaceId) { toast.error('Please select or create a workspace first'); return }
    setIsSubmitting(true)
    setAppState('plan_loading')
    try {
      const preview = await api.generatePlan({ query: query.trim(), model, depth, mode, provider, workspace_id: selectedWorkspaceId })
      setPlanPreview(preview)
      setPlanQuery(query.trim())
      setAppState('plan_review')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Plan generation failed')
      setAppState('idle')
    } finally { setIsSubmitting(false) }
  }, [query, model, depth, mode, provider, selectedWorkspaceId])

  const handleApproveAndStart = useCallback((steps: string[], subQueries: string[], exportFormats: string[]) => {
    if (!selectedWorkspaceId) { toast.error('Please select or create a workspace first'); return }
    setStreamEvents([])
    setIsStreaming(true)
    setAppState('streaming')
    setActiveTab('progress')

    const controller = api.streamApprovedPlan(
      { query: planQuery, plan: { steps }, sub_queries: subQueries, model, depth, mode, provider, export_formats: exportFormats, workspace_id: selectedWorkspaceId },
      (event) => setStreamEvents((prev) => [...prev, event]),
      (data) => {
        setIsStreaming(false)
        if (data.run_id) {
          setSelectedRunId(data.run_id)
          setRefreshKey(k => k + 1)
          setActiveTab('citations')
          setAppState('results')
        }
      },
      (errorMsg) => { setIsStreaming(false); toast.error(errorMsg) }
    )
    abortRef.current = controller
  }, [planQuery, model, depth, mode, provider, selectedWorkspaceId])

  const handleQuickStart = useCallback(async () => {
    const validation = researchSchema.safeParse({ query, model, depth, mode, provider })
    if (!validation.success) {
      toast.error(validation.error.issues[0].message)
      return
    }
    if (!selectedWorkspaceId) { toast.error('Please select or create a workspace first'); return }
    setIsSubmitting(true)
    setStreamEvents([])
    setIsStreaming(true)
    setAppState('streaming')
    setActiveTab('progress')

    const controller = api.streamResearch(
      { query: query.trim(), model, depth, mode, provider, workspace_id: selectedWorkspaceId },
      (event) => setStreamEvents((prev) => [...prev, event]),
      (data) => {
        setIsStreaming(false)
        setIsSubmitting(false)
        if (data.run_id) {
          setSelectedRunId(data.run_id)
          setRefreshKey(k => k + 1)
          setActiveTab('citations')
          setAppState('results')
        }
      },
      (errorMsg) => { setIsStreaming(false); setIsSubmitting(false); toast.error(errorMsg) }
    )
    abortRef.current = controller
    setQuery('')
  }, [query, model, depth, mode, provider, selectedWorkspaceId])

  const resetToIdle = useCallback(() => {
    setPlanPreview(null)
    setPlanQuery('')
    setStreamEvents([])
    setIsStreaming(false)
    setAppState('idle')
    setSelectedRunId(null)
    if (abortRef.current) { abortRef.current.abort(); abortRef.current = null }
  }, [])

  // ─── Sidebar Content ───────────────────────────────────────────
  const sidebarContent = (
    <div className="flex flex-col h-full p-3 gap-3">
      {/* Workspace Selector */}
      <WorkspaceSelector
        selectedWorkspaceId={selectedWorkspaceId}
        onWorkspaceSelect={setSelectedWorkspaceId}
      />

      {/* Mode switcher */}
      <div className="flex bg-white/[0.03] rounded-xl p-0.5">
        {(['research', 'code-arch'] as const).map((v) => (
          <button
            key={v}
            onClick={() => setGlobalView(v)}
            className={cn(
              'flex-1 px-2 py-1.5 text-xs font-medium rounded-lg transition-all duration-150 cursor-pointer border-none',
              globalView === v
                ? 'bg-white/[0.06] text-[#e0e0e0]'
                : 'text-[#555] hover:text-[#999]'
            )}
          >
            {v === 'research' ? 'Research' : 'Code Arch'}
          </button>
        ))}
      </div>

      {globalView === 'research' && (
        <>
          <button
            onClick={resetToIdle}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl text-sm font-medium text-[#e0e0e0] bg-[#c8956c]/15 hover:bg-[#c8956c]/25 transition-colors duration-150 cursor-pointer border-none"
          >
            <Plus className="w-4 h-4" />
            New Research
          </button>

          <div className="flex-1 overflow-hidden flex flex-col min-h-0">
            <div className="text-[10px] uppercase tracking-wider text-[#555] font-semibold mb-2 px-1">
              Research Runs
            </div>
            <div className="flex-1 overflow-y-auto min-h-0">
              <RunList
                key={refreshKey}
                selectedRunId={selectedRunId}
                selectedWorkspaceId={selectedWorkspaceId}
                onSelectRun={(id) => {
                  resetToIdle()
                  setSelectedRunId(id)
                  setActiveTab('citations')
                  setAppState('results')
                }}
              />
            </div>
          </div>
        </>
      )}

      {globalView === 'code-arch' && (
        <div className="flex flex-col gap-2 text-xs text-[#999] pt-2">
          <div className="text-[10px] uppercase tracking-wider text-[#555] font-semibold">GITNEXUS WEB UI</div>
          <p>
            The official interactive graph at{' '}
            <a href="https://gitnexus.vercel.app" target="_blank" rel="noreferrer" className="text-[#d4a574]">
              gitnexus.vercel.app
            </a>
            {' '}auto-connects to your local codebase via the bridge server on port 4747.
          </p>
          <p>Click <strong>Start Local Server</strong> in the main panel to begin.</p>
        </div>
      )}

      {/* Sign Out */}
      <div className="mt-auto pt-3 border-t border-white/[0.06] flex items-center justify-between gap-2">
        <span className="text-xs text-[#555] truncate max-w-[140px]">{user?.email}</span>
        <button
          onClick={signOut}
          className="text-xs text-[#c45a5a] hover:text-[#e0e0e0] transition-colors duration-150 cursor-pointer bg-transparent border-none"
        >
          Sign Out
        </button>
      </div>
    </div>
  )

  // ─── Main Content ──────────────────────────────────────────────
  const mainContent = (
    <div className="flex-1 overflow-hidden flex flex-col relative">
      {/* Plan Review */}
      {globalView !== 'code-arch' && appState === 'plan_review' && planPreview && (
        <PlanReview
          preview={planPreview}
          query={planQuery}
          onApprove={handleApproveAndStart}
          onRegenerate={() => setAppState('idle')}
          isLoading={isSubmitting}
        />
      )}

      {/* Plan Loading */}
      {globalView !== 'code-arch' && appState === 'plan_loading' && (
        <div className="flex-1 flex flex-col items-center justify-center text-[#999]">
          <div className="w-8 h-8 border-2 border-[#c8956c]/30 border-t-[#c8956c] rounded-full animate-spin mb-4" />
          <h3 className="text-lg font-semibold text-[#e0e0e0] mb-1">Generating Research Plan…</h3>
          <p className="text-sm">The AI is creating a comprehensive plan for your query.</p>
        </div>
      )}

      {/* Streaming */}
      {globalView !== 'code-arch' && appState === 'streaming' && (
        <ResearchProgress events={streamEvents} isActive={isStreaming} />
      )}

      {/* Results */}
      {(appState === 'results' || appState === 'idle') && selectedRunId && globalView !== 'code-arch' && (
        <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-0">
          <div className="overflow-y-auto p-6">
            <ReportView runId={selectedRunId} />
          </div>
          <div className="overflow-y-auto border-l border-white/[0.06] p-6">
            <div className="flex gap-0 mb-4">
              {[
                { id: 'citations', label: 'Citations', icon: Quote },
                { id: 'export', label: 'Export', icon: Download },
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-t-lg border-b-2 transition-all duration-150 cursor-pointer border-none bg-transparent',
                    activeTab === t.id
                      ? 'text-[#c8956c] border-b-[#c8956c]'
                      : 'text-[#555] border-b-transparent hover:text-[#999]'
                  )}
                >
                  <t.icon className="w-4 h-4" />
                  {t.label}
                </button>
              ))}
            </div>
            {activeTab === 'citations' && <CitationsView runId={selectedRunId} />}
            {activeTab === 'export' && <ExportPanel runId={selectedRunId} />}
          </div>
        </div>
      )}

      {/* Idle Hero */}
      {appState === 'idle' && !selectedRunId && globalView !== 'code-arch' && (
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl mx-auto space-y-8">
            {/* Hero */}
            <div className="text-center space-y-2">
              <h1 className="text-4xl font-extrabold tracking-tight">
                Deep Research <span className="text-[#c8956c]">Engine</span>
              </h1>
              <p className="text-[#999] text-lg">Autonomous Web-Scale Scraper & Citation Compiler</p>
            </div>

            {/* Query Composer */}
            <div className="liquid-glass rounded-2xl p-6 space-y-4">
              <div>
                <label className="text-xs uppercase tracking-wider text-[#555] font-semibold block mb-2">
                  Research Objective
                </label>
                <textarea
                  placeholder="What are the latest breakthroughs in high-temperature superconductors?"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 text-[#e0e0e0] placeholder:text-[#555] font-mono text-sm resize-y min-h-[80px] focus:outline-none focus:border-[#c8956c]/50"
                />
                <div className="mt-2 flex justify-between items-center">
                  <TokenCounter text={query} model="gpt-4" maxTokens={4096} />
                </div>
              </div>

              {/* Presets */}
              <div className="flex flex-wrap gap-2">
                {PRESETS.map((preset, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setQuery(preset.query)
                      setProvider(preset.provider as 'openrouter' | 'groq')
                      setMode(preset.mode as 'web' | 'github')
                      setModel(preset.model)
                      setDepth(preset.depth)
                    }}
                    className="px-3 py-1 text-xs rounded-lg border border-[#c8956c]/30 text-[#c8956c] hover:bg-[#c8956c]/10 transition-colors duration-150 cursor-pointer"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>

              {/* Controls Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs uppercase tracking-wider text-[#555] font-semibold block mb-2">LLM Provider</label>
                  <div className="flex bg-white/[0.03] rounded-xl p-0.5">
                    {(['openrouter', 'groq'] as const).map((p) => (
                      <button
                        key={p}
                        onClick={() => handleProviderChange(p)}
                        className={cn(
                          'flex-1 px-3 py-2 text-xs rounded-lg transition-all duration-150 cursor-pointer border-none',
                          provider === p ? 'bg-white/[0.06] text-[#e0e0e0]' : 'text-[#555] hover:text-[#999]'
                        )}
                      >
                        {p === 'openrouter' ? '🌐 OpenRouter' : '⚡ Groq'}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs uppercase tracking-wider text-[#555] font-semibold block mb-2">Target Corpus</label>
                  <div className="flex bg-white/[0.03] rounded-xl p-0.5">
                    {(['web', 'github'] as const).map((m) => (
                      <button
                        key={m}
                        onClick={() => setMode(m)}
                        className={cn(
                          'flex-1 px-3 py-2 text-xs rounded-lg transition-all duration-150 cursor-pointer border-none',
                          mode === m ? 'bg-white/[0.06] text-[#e0e0e0]' : 'text-[#555] hover:text-[#999]'
                        )}
                      >
                        {m === 'web' ? '🌐 Web-Scale' : '📁 Local Repo'}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs uppercase tracking-wider text-[#555] font-semibold block mb-2">Model ID</label>
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-2.5 text-sm font-mono text-[#e0e0e0] focus:outline-none focus:border-[#c8956c]/50"
                  />
                </div>
                <div>
                  <label className="text-xs uppercase tracking-wider text-[#555] font-semibold block mb-2">
                    Depth: {depth} ({depth === 1 ? 'Quick — 6 rounds' : depth === 3 ? 'Standard — 18 rounds' : 'Exhaustive — 30 rounds'})
                  </label>
                  <input
                    type="range"
                    min={1}
                    max={5}
                    step={1}
                    value={depth}
                    onChange={(e) => setDepth(Number(e.target.value))}
                    className="w-full accent-[#c8956c]"
                  />
                  <div className="flex justify-between text-[10px] text-[#555] mt-1">
                    <span>Quick</span>
                    <span>Standard</span>
                    <span>Exhaustive</span>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleGeneratePlan}
                  disabled={!query.trim() || !selectedWorkspaceId || isSubmitting}
                  className="flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-medium bg-[#c8956c]/15 text-[#c8956c] hover:bg-[#c8956c]/25 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150 cursor-pointer border-none"
                >
                  <ListChecks className="w-4 h-4" />
                  Generate Plan
                </button>
                <button
                  onClick={handleQuickStart}
                  disabled={!query.trim() || !selectedWorkspaceId || isSubmitting}
                  className="flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-medium border border-[#c8956c]/30 text-[#c8956c] hover:bg-[#c8956c]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150 cursor-pointer"
                >
                  <FlaskConical className="w-4 h-4" />
                  Quick Start
                </button>
              </div>
            </div>

            {/* Bento Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <TerminalDemo />

              {/* Telemetry */}
              <div className="liquid-glass rounded-2xl p-6 flex flex-col min-h-[420px]">
                <div className="mb-4">
                  <h4 className="text-lg font-bold text-[#e0e0e0]">System Engine Status</h4>
                  <p className="text-sm text-[#999]">Real-time stats from local caches & circuit breakers.</p>
                </div>
                <div className="grid grid-cols-2 gap-3 flex-1">
                  {[
                    { label: 'Query Key Cache', value: telemetry?.total_cached_queries ?? 0, sub: 'query_cache table size' },
                    { label: 'Scraped Document Cache', value: telemetry?.total_scraped_pages ?? 0, sub: 'page_cache table size' },
                    { label: 'HTTP Success Rate', value: telemetry ? `${telemetry.scraper_success_rate}%` : '100.0%', sub: 'successful page fetches' },
                    { label: 'Domain Breakers Open', value: telemetry?.active_circuit_breakers.length ?? 0, sub: 'OPEN breakers (cooldown)', alert: telemetry && telemetry.active_circuit_breakers.length > 0 },
                  ].map((stat) => (
                    <div key={stat.label} className="bg-white/[0.03] rounded-xl p-4 flex flex-col justify-center border border-white/[0.04]">
                      <div className="text-[10px] uppercase tracking-wider text-[#555] font-semibold">{stat.label}</div>
                      <div className={cn('text-2xl font-extrabold mt-1 font-mono', stat.alert ? 'text-[#c45a5a]' : 'text-[#c8956c]')}>{stat.value}</div>
                      <div className="text-[10px] text-[#555] mt-1">{stat.sub}</div>
                    </div>
                  ))}
                </div>
                {telemetry && telemetry.active_circuit_breakers.length > 0 && (
                  <div className="mt-3 p-2 rounded-lg bg-[#c45a5a]/10 border border-[#c45a5a]/20">
                    <div className="text-xs text-[#c45a5a] font-semibold mb-1">⚠️ OPEN CIRCUITS:</div>
                    <div className="flex flex-wrap gap-1">
                      {telemetry.active_circuit_breakers.map((domain, i) => (
                        <span key={i} className="px-2 py-0.5 text-[10px] bg-[#c45a5a]/20 text-[#c45a5a] rounded-md">{domain}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Code Architecture */}
      {globalView === 'code-arch' && <GitNexusWebView />}
    </div>
  )

  return (
    <Layout
      sidebar={sidebarContent}
      userEmail={user?.email}
      onSignOut={signOut}
    >
      {mainContent}
    </Layout>
  )
}
