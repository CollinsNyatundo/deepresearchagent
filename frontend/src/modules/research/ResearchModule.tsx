import { useEffect } from 'react'
import { Plus, FlaskConical, ListChecks, Download, Quote, ChevronLeft, ChevronRight, Settings2, Database, FileText, Activity, ShieldCheck, Map, Network } from 'lucide-react'

import { RunList } from '../../components/runs/RunList'
import { ReportView } from '../../components/views/ReportView'
import { CitationsView } from '../../components/views/CitationsView'
import { GitNexusWebView } from '../../components/code-arch/GitNexusWebView'
import { ResearchProgress } from '../../components/views/ResearchProgress'
import { PlanReview } from '../../components/views/PlanReview'
import { ExportPanel } from '../../components/views/ExportPanel'
import { MindmapView } from '../../components/views/MindmapView'
import { KnowledgeGraphView } from '../../components/knowledge-graph/KnowledgeGraphView'
import { api } from '../../api/client'
import { useAuth } from '../../lib/authContext'
import { useResearch } from '../../lib/researchContext'
import Layout from '../../components/layout/Layout'
import { cn } from '../../lib/utils'
import { TokenCounter } from '../../components/TokenCounter'

const PRESETS = [
  { label: '⚡ Superconductivity', query: 'What are the latest breakthroughs in high-temperature superconductors?', provider: 'openrouter', model: 'nvidia/nemotron-3-super-120b-a12b:free', depth: 3, mode: 'web' },
  { label: '🦙 Llama Spec', query: 'Analyze Llama 3.3 70B performance compared to Claude 3.5 Sonnet', provider: 'groq', model: 'llama-3.3-70b-versatile', depth: 2, mode: 'web' },
  { label: '📘 TS Decorators', query: 'Explain TypeScript 5.0 decorators and provide comparison to stage 2 decorators', provider: 'openrouter', model: 'qwen/qwen3-235b-a22b:free', depth: 1, mode: 'web' },
]

export default function ResearchModule() {
  const { user, signOut } = useAuth()
  const {
    selectedWorkspaceId,
    selectedRunId,
    setSelectedRunId,
    activeTab,
    setActiveTab,
    refreshKey,
    globalView,
    setGlobalView,
    appState,
    setAppState,
    resultsSidebarExpanded,
    setResultsSidebarExpanded,
    advancedOpen,
    setAdvancedOpen,
    query,
    setQuery,
    model,
    setModel,
    provider,
    setProvider,
    depth,
    setDepth,
    mode,
    setMode,
    isSubmitting,
    planPreview,
    planQuery,
    streamEvents,
    isStreaming,
    telemetry,
    fetchTelemetry,
    handleProviderChange,
    handleGeneratePlan,
    handleApproveAndStart,
    handleQuickStart,
    resetToIdle,
    reconnectToRun,
  } = useResearch()

  useEffect(() => {
    if (appState === 'idle' && !selectedRunId) fetchTelemetry()
  }, [appState, selectedRunId, fetchTelemetry])


  // ─── Sidebar Content ───────────────────────────────────────────
  const sidebarContent = (
    <div className="flex flex-col h-full py-3 gap-0.5">
      {/* View mode toggle */}
      <div className="px-3 mb-2">
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
      </div>

      {globalView === 'research' && (
        <>
          {/* Actions */}
          <div className="px-3 mb-1">
            <p className="sidebar-section-label">Actions</p>
            <button
              onClick={resetToIdle}
              className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-xl text-xs font-medium text-[#e0e0e0] bg-[#c8956c]/15 hover:bg-[#c8956c]/25 transition-colors duration-150 cursor-pointer border-none"
            >
              <Plus className="w-3.5 h-3.5" />
              New Research
            </button>
          </div>

          {/* Research Runs */}
          <div className="px-3 flex-1 overflow-hidden flex flex-col min-h-0">
            <p className="sidebar-section-label">Research Runs</p>
            <div className="flex-1 overflow-y-auto min-h-0">
              <RunList
                key={refreshKey}
                selectedRunId={selectedRunId}
                selectedWorkspaceId={selectedWorkspaceId}
                onSelectRun={async (id) => {
                  try {
                    const details = await api.getRunDetails(id)
                    if (details.status !== 'complete' && details.status !== 'failed') {
                      reconnectToRun(id)
                    } else {
                      resetToIdle()
                      setSelectedRunId(id)
                      setActiveTab('report')
                      setAppState('results')
                    }
                  } catch (err) {
                    reconnectToRun(id)
                  }
                }}
              />
            </div>
          </div>
        </>
      )}

      {globalView === 'code-arch' && (
        <div className="px-3 flex flex-col gap-2 text-xs text-[#999] pt-2">
          <p className="sidebar-section-label">GitNexus Web UI</p>
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
        <div className="flex-1 flex overflow-hidden h-full">
          {/* Inner Collapsible Sidebar */}
          <div
            className={cn(
              "flex-shrink-0 border-r border-white/[0.06] bg-black/40 backdrop-blur-md flex flex-col transition-all duration-300 relative select-none",
              resultsSidebarExpanded ? "w-52" : "w-12"
            )}
          >
            {/* Collapse Toggle Button */}
            <div className="p-2 flex justify-end border-b border-white/[0.06]">
              <button
                onClick={() => setResultsSidebarExpanded(!resultsSidebarExpanded)}
                className="p-1 rounded-lg text-[#555] hover:text-[#e0e0e0] hover:bg-white/[0.03] transition-all cursor-pointer border-none bg-transparent"
                title={resultsSidebarExpanded ? "Collapse Sidebar" : "Expand Sidebar"}
              >
                {resultsSidebarExpanded ? (
                  <ChevronLeft className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </button>
            </div>

            {/* Sidebar View Navigation Items */}
            <nav className="flex-1 py-3 flex flex-col gap-1 px-1.5">
              {[
                { id: 'report', label: 'Research Report', icon: FileText },
                { id: 'mindmap', label: 'Concept Mindmap', icon: Map },
                { id: 'graph', label: 'Knowledge Graph', icon: Network },
                { id: 'citations', label: 'Source Citations', icon: Quote },
                { id: 'export', label: 'Export Options', icon: Download },
              ].map((item) => {
                const isActive = activeTab === item.id
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 text-xs font-semibold rounded-xl transition-all cursor-pointer border-none bg-transparent text-left",
                      isActive
                        ? "bg-[#c8956c]/15 text-[#c8956c] shadow-sm shadow-[#c8956c]/5"
                        : "text-[#555] hover:text-[#999] hover:bg-white/[0.02]"
                    )}
                    title={item.label}
                  >
                    <item.icon className={cn("w-4 h-4 shrink-0", isActive ? "text-[#c8956c]" : "text-current")} />
                    {resultsSidebarExpanded && (
                      <span className="truncate">{item.label}</span>
                    )}
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Results Main Canvas Area */}
          <div className="flex-1 overflow-hidden flex flex-col h-full bg-black">
            {activeTab === 'report' && (
              <div className="flex-1 overflow-y-auto p-6 md:p-8 max-w-4xl mx-auto w-full">
                <ReportView runId={selectedRunId} />
              </div>
            )}
            {activeTab === 'mindmap' && (
              <div className="flex-1 overflow-hidden p-6 h-full">
                <MindmapView runId={selectedRunId} />
              </div>
            )}
            {activeTab === 'graph' && (
              <div className="flex-1 overflow-hidden p-6 h-full">
                <KnowledgeGraphView runId={selectedRunId} />
              </div>
            )}
            {activeTab === 'citations' && (
              <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full">
                <div className="mb-6 px-8 pt-4">
                  <h2 className="text-xl font-bold text-[#e0e0e0] flex items-center gap-2">
                    <Quote className="w-5 h-5 text-[#c8956c]" />
                    Source Citations
                  </h2>
                  <p className="text-xs text-[#555] mt-1">Verified references compiled during research.</p>
                </div>
                <CitationsView runId={selectedRunId} />
              </div>
            )}
            {activeTab === 'export' && (
              <div className="flex-1 overflow-y-auto p-6 max-w-xl mx-auto w-full flex flex-col justify-center">
                <div className="mb-6 text-center">
                  <Download className="w-8 h-8 text-[#c8956c] mx-auto mb-2" />
                  <h2 className="text-xl font-bold text-[#e0e0e0]">Export Findings</h2>
                  <p className="text-xs text-[#555] mt-1">Compile your report in multiple formats.</p>
                </div>
                <div className="liquid-glass rounded-2xl p-6">
                  <ExportPanel runId={selectedRunId} />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Idle Hero */}
      {appState === 'idle' && !selectedRunId && globalView !== 'code-arch' && (
        <div className="flex-1 overflow-y-auto p-6 md:p-12">
          <div className="max-w-3xl mx-auto space-y-8 flex flex-col justify-center min-h-[80vh]">
            {/* Hero */}
            <div className="text-center space-y-3">
              <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight" style={{ fontFamily: 'Fira Sans' }}>
                Deep Research <span className="text-[#c8956c]">Engine</span>
              </h1>
              <p className="text-[#999] text-base md:text-lg">Autonomous Web-Scale Scraper & Citation Compiler</p>
            </div>

            {/* Query Composer */}
            <div className="liquid-glass rounded-2xl p-6 space-y-5">
              <div>
                <label className="text-[10px] uppercase tracking-wider text-[#555] font-bold block mb-2">
                  Research Objective
                </label>
                <textarea
                  placeholder="What are the latest breakthroughs in high-temperature superconductors?"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full bg-white/[0.02] border border-white/[0.06] rounded-xl p-4 text-[#e0e0e0] placeholder:text-[#444] font-mono text-sm resize-y min-h-[90px] focus:outline-none focus:border-[#c8956c]/40 focus:ring-1 focus:ring-[#c8956c]/20 transition-all"
                />
                <div className="mt-1 flex justify-between items-center text-[10px] text-[#555]">
                  <TokenCounter text={query} model="gpt-4" maxTokens={4096} />
                </div>
              </div>

              {/* Presets */}
              <div className="flex flex-wrap gap-1.5">
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
                    className="px-2.5 py-1 text-[11px] rounded-lg border border-[#c8956c]/20 text-[#c8956c]/70 hover:text-[#c8956c] hover:bg-[#c8956c]/5 transition-all duration-150 cursor-pointer bg-transparent"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>

              {/* Advanced Settings Toggle */}
              <div className="pt-1">
                <button
                  onClick={() => setAdvancedOpen(!advancedOpen)}
                  className="flex items-center gap-1.5 text-xs text-[#555] hover:text-[#999] transition-colors cursor-pointer border-none bg-transparent"
                >
                  <Settings2 className="w-3.5 h-3.5" />
                  <span>{advancedOpen ? 'Hide' : 'Show'} Advanced Settings</span>
                </button>
              </div>

              {/* Expandable Advanced Options */}
              {advancedOpen && (
                <div className="space-y-4 pt-3 border-t border-white/[0.04] animate-in fade-in slide-in-from-top-2 duration-200">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="text-[10px] uppercase tracking-wider text-[#555] font-semibold block mb-2">LLM Provider</label>
                      <div className="flex bg-white/[0.02] rounded-xl p-0.5 border border-white/[0.04]">
                        {(['openrouter', 'groq'] as const).map((p) => (
                          <button
                            key={p}
                            onClick={() => handleProviderChange(p)}
                            className={cn(
                              'flex-1 px-3 py-1.5 text-xs rounded-lg transition-all duration-150 cursor-pointer border-none',
                              provider === p ? 'bg-white/[0.06] text-[#e0e0e0]' : 'text-[#555] hover:text-[#999] bg-transparent'
                            )}
                          >
                            {p === 'openrouter' ? '🌐 OpenRouter' : '⚡ Groq'}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] uppercase tracking-wider text-[#555] font-semibold block mb-2">Target Corpus</label>
                      <div className="flex bg-white/[0.02] rounded-xl p-0.5 border border-white/[0.04]">
                        {(['web', 'github'] as const).map((m) => (
                          <button
                            key={m}
                            onClick={() => setMode(m)}
                            className={cn(
                              'flex-1 px-3 py-1.5 text-xs rounded-lg transition-all duration-150 cursor-pointer border-none',
                              mode === m ? 'bg-white/[0.06] text-[#e0e0e0]' : 'text-[#555] hover:text-[#999] bg-transparent'
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
                      <label className="text-[10px] uppercase tracking-wider text-[#555] font-semibold block mb-2">Model ID</label>
                      <input
                        type="text"
                        value={model}
                        onChange={(e) => setModel(e.target.value)}
                        className="w-full bg-white/[0.02] border border-white/[0.06] rounded-xl px-4 py-2.5 text-xs font-mono text-[#e0e0e0] focus:outline-none focus:border-[#c8956c]/40"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] uppercase tracking-wider text-[#555] font-semibold block mb-2">
                        Depth: {depth} ({depth === 1 ? 'Quick — 6 rounds' : depth === 3 ? 'Standard — 18 rounds' : 'Exhaustive — 30 rounds'})
                      </label>
                      <input
                        type="range"
                        min={1}
                        max={5}
                        step={1}
                        value={depth}
                        onChange={(e) => setDepth(Number(e.target.value))}
                        className="w-full accent-[#c8956c] bg-white/[0.06] h-1.5 rounded-lg appearance-none cursor-pointer"
                      />
                      <div className="flex justify-between text-[9px] text-[#555] mt-1">
                        <span>Quick</span>
                        <span>Standard</span>
                        <span>Exhaustive</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleGeneratePlan}
                  disabled={!query.trim() || !selectedWorkspaceId || isSubmitting}
                  className="flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-semibold bg-[#c8956c]/15 text-[#c8956c] hover:bg-[#c8956c]/25 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-150 cursor-pointer border-none"
                >
                  <ListChecks className="w-4 h-4" />
                  Generate Plan
                </button>
                <button
                  onClick={handleQuickStart}
                  disabled={!query.trim() || !selectedWorkspaceId || isSubmitting}
                  className="flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-semibold border border-[#c8956c]/20 text-[#c8956c] hover:bg-[#c8956c]/5 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-150 cursor-pointer bg-transparent"
                >
                  <FlaskConical className="w-4 h-4" />
                  Quick Start
                </button>
              </div>
            </div>

            {/* System Status Row */}
            <div className="liquid-glass rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 text-xs text-[#999] border border-white/[0.04]">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#7dac5a] animate-pulse" />
                <span className="font-semibold text-[#e0e0e0]">System Engine Active</span>
              </div>
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                <div className="flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-[#c8956c]" />
                  <span>Queries Cached: <strong className="font-mono text-[#e0e0e0]">{telemetry?.total_cached_queries ?? 0}</strong></span>
                </div>
                <div className="flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-[#c8956c]" />
                  <span>Scraped Pages: <strong className="font-mono text-[#e0e0e0]">{telemetry?.total_scraped_pages ?? 0}</strong></span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-[#c8956c]" />
                  <span>Success Rate: <strong className="font-mono text-[#e0e0e0]">{telemetry ? `${telemetry.scraper_success_rate}%` : '100.0%'}</strong></span>
                </div>
                <div className="flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#c8956c]" />
                  <span>Circuits: <strong className="font-mono text-[#e0e0e0]">{telemetry?.active_circuit_breakers.length ?? 0}</strong></span>
                </div>
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
