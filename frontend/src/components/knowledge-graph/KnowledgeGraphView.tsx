/**
 * KnowledgeGraphView — Force-directed knowledge graph visualization.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import {
  ExternalLink, RefreshCw, ZoomIn, ZoomOut, Focus, AlertTriangle,
  Crown, Network, Search, FileCode
} from 'lucide-react';
import { api } from '../../api/client';
import type { KnowledgeGraph, KGNode } from '../../types/api';
import { CommunityLegend, getCommunityColor } from './CommunityLegend';
import { KGStatsPanel } from './KGStatsPanel';
import { KGQueryPanel } from './KGQueryPanel';

interface KnowledgeGraphViewProps {
  runId: string;
}

function getNodeSize(degree: number): number {
  if (degree > 20) return 38;
  if (degree > 10) return 28;
  if (degree > 5) return 22;
  if (degree > 2) return 18;
  return 14;
}

function getEdgeStyle(provenance: string) {
  switch (provenance) {
    case 'INFERRED': return { lineDash: [6, 4] };
    case 'AMBIGUOUS': return { lineDash: [2, 4] };
    default: return { lineDash: [0, 0] };
  }
}

function getEdgeColor(type: string): string {
  const typeColors: Record<string, string> = {
    calls: '#4F46E5', imports: '#059669', rationale_for: '#D97706',
    semantically_similar_to: '#6B7280', has_step: '#7C3AED', references: '#0891B2',
  };
  return typeColors[type] || '#6B7280';
}

export function KnowledgeGraphView({ runId }: KnowledgeGraphViewProps) {
  const graphRef = useRef<HTMLDivElement>(null);
  const g6Instance = useRef<any>(null);

  const [kg, setKg] = useState<KnowledgeGraph | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isBuilding, setIsBuilding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notBuilt, setNotBuilt] = useState(false);

  const [hiddenCommunities, setHiddenCommunities] = useState<Set<number>>(new Set());
  const [selectedNode, setSelectedNode] = useState<KGNode | null>(null);
  const [popoverOpened, setPopoverOpened] = useState(false);
  const [activeTab, setActiveTab] = useState<'graph' | 'query'>('graph');

  const loadKg = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setNotBuilt(false);
    try {
      const data = await api.getKnowledgeGraph(runId);
      setKg(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load knowledge graph';
      if (msg.includes('404') || msg.includes('not built') || msg.includes('503')) {
        setNotBuilt(true);
      } else {
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [runId]);

  useEffect(() => { loadKg(); }, [loadKg]);

  const handleBuild = async () => {
    setIsBuilding(true);
    setError(null);
    try {
      const built = await api.buildKnowledgeGraph(runId);
      setKg(built);
      setNotBuilt(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Build failed');
    } finally {
      setIsBuilding(false);
    }
  };

  useEffect(() => {
    if (!kg || !graphRef.current || activeTab !== 'graph') return;

    if (g6Instance.current) {
      try { g6Instance.current.destroy(); } catch {}
      g6Instance.current = null;
    }

    const container = graphRef.current;
    const width = container.offsetWidth || 800;
    const height = container.offsetHeight || 600;

    let isDestroyed = false;
    let resizeObserver: ResizeObserver | null = null;

    import('@antv/g6').then(({ Graph }) => {
      if (isDestroyed) return;

      const visibleNodes = kg.nodes.filter((n) => !hiddenCommunities.has(n.community));
      const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));
      const visibleEdges = kg.edges.filter((e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target));

      const graphData = {
        nodes: visibleNodes.map((node) => ({
          id: node.id,
          label: node.label.length > 20 ? node.label.slice(0, 20) + '…' : node.label,
          style: {
            size: getNodeSize(node.degree),
            fill: getCommunityColor(node.community),
            stroke: node.is_god_node ? '#FFD700' : '#1e293b',
            lineWidth: node.is_god_node ? 3 : 1,
            fillOpacity: node.provenance === 'AMBIGUOUS' ? 0.5 : 1,
          },
          data: node,
        })),
        edges: visibleEdges.map((edge, i) => ({
          id: `edge-${i}`,
          source: edge.source,
          target: edge.target,
          label: edge.label || edge.type,
          style: {
            stroke: getEdgeColor(edge.type),
            lineWidth: Math.max(1, edge.confidence * 2),
            opacity: 0.6,
            ...getEdgeStyle(edge.provenance),
          },
          data: edge,
        })),
      };

      const graph = new Graph({
        container, width, height, data: graphData,
        layout: {
          type: 'force', preventOverlap: true, nodeSize: 30,
          linkDistance: 120, nodeStrength: -80, edgeStrength: 0.4, iterations: 300,
        },
        node: {
          type: 'circle',
          style: { labelPlacement: 'bottom', labelFontSize: 10, labelFill: '#e2e8f0', labelMaxWidth: 80 },
        },
        edge: { type: 'line', style: { labelFontSize: 9, labelFill: '#94a3b8', endArrow: true } },
        behaviors: ['zoom-canvas', 'drag-canvas', 'drag-node'],
        autoFit: 'view', animation: false, theme: 'dark',
      });

      graph.on('node:click', (evt: any) => {
        const nodeData = evt.target?.getModel?.()?.data || evt.itemType === 'node' ? evt.target : null;
        if (nodeData) {
          const originalNode = kg.nodes.find((n) => n.id === (nodeData.id || nodeData.data?.id));
          if (originalNode) { setSelectedNode(originalNode); setPopoverOpened(true); }
        }
      });

      graph.render();
      g6Instance.current = graph;

      resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const { width: newWidth, height: newHeight } = entry.contentRect;
          if (g6Instance.current && newWidth > 0 && newHeight > 0) {
            try { g6Instance.current.setSize(newWidth, newHeight); } catch (err) { console.error('G6 resize error:', err); }
          }
        }
      });
      resizeObserver.observe(container);
    }).catch((err) => { console.warn('G6 import failed:', err); });

    return () => {
      isDestroyed = true;
      if (resizeObserver) resizeObserver.disconnect();
      if (g6Instance.current) { try { g6Instance.current.destroy(); } catch {} g6Instance.current = null; }
    };
  }, [kg, hiddenCommunities, activeTab]);

  useEffect(() => {
    const handleHighlight = (e: Event) => {
      const customEvent = e as CustomEvent<{ url: string; id: string }>;
      const { url } = customEvent.detail;
      if (!g6Instance.current || !kg || !url) return;
      try {
        const domain = new URL(url).hostname.replace('www.', '');
        const nodesToHighlight: string[] = [];
        kg.nodes.forEach((n) => {
          if (n.summary?.toLowerCase().includes(domain.toLowerCase()) || n.label.toLowerCase().includes(domain.toLowerCase())) {
            nodesToHighlight.push(n.id);
          }
        });
        if (nodesToHighlight.length > 0) {
          const nodes = g6Instance.current.getNodes?.();
          if (nodes) {
            nodes.forEach((nodeItem: any) => {
              const model = nodeItem.getModel?.() || nodeItem;
              const nodeId = model.id || model.data?.id;
              if (nodesToHighlight.includes(nodeId)) g6Instance.current.setItemState(nodeItem, 'selected', true);
            });
          }
        }
      } catch (err) { console.warn('Highlight failed:', err); }
    };
    const handleClearHighlight = () => {
      if (!g6Instance.current || !kg) return;
      try {
        const nodes = g6Instance.current.getNodes?.();
        if (nodes) { nodes.forEach((nodeItem: any) => { g6Instance.current.setItemState(nodeItem, 'selected', false); }); }
      } catch (err) { console.error('Failed to clear highlight:', err); }
    };
    window.addEventListener('highlight-citation', handleHighlight);
    window.addEventListener('clear-highlight-citation', handleClearHighlight);
    return () => {
      window.removeEventListener('highlight-citation', handleHighlight);
      window.removeEventListener('clear-highlight-citation', handleClearHighlight);
    };
  }, [kg]);

  const handleToggleCommunity = useCallback((id: number) => {
    setHiddenCommunities((prev) => { const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  }, []);

  const handleZoomIn = () => g6Instance.current?.zoom(1.2);
  const handleZoomOut = () => g6Instance.current?.zoom(0.8);
  const handleFit = () => g6Instance.current?.fitView(20);

  const handleGodNodeClick = useCallback((nodeId: string) => {
    if (!g6Instance.current) return;
    try {
      const item = g6Instance.current.findById?.(nodeId);
      if (item) { g6Instance.current.focusItem(item); g6Instance.current.setItemState(item, 'selected', true); }
    } catch {}
    setActiveTab('graph');
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <div className="w-10 h-10 border-2 border-[#333] border-t-[#c8956c] rounded-full animate-spin" />
        <h4 className="text-lg font-bold text-[#e0e0e0]">Loading Knowledge Graph...</h4>
        <p className="text-sm text-[#555]">This may take a moment for large graphs.</p>
      </div>
    );
  }

  if (notBuilt) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-6">
        <div className="w-20 h-20 rounded-full bg-[#c8956c]/10 flex items-center justify-center">
          <Network className="w-10 h-10 text-[#c8956c]" />
        </div>
        <div className="text-center max-w-lg">
          <h3 className="text-xl font-bold text-[#e0e0e0] mb-2">Knowledge Graph Not Built</h3>
          <p className="text-sm text-[#999]">
            The knowledge graph for this run hasn't been built yet. Building converts the research findings into a structured, navigable graph with automatic community detection and cross-domain relationship discovery.
          </p>
        </div>
        <button
          onClick={handleBuild}
          disabled={isBuilding}
          className="flex items-center gap-2 py-3 px-6 rounded-xl text-sm font-medium bg-[#c8956c]/15 text-[#c8956c] hover:bg-[#c8956c]/25 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150 cursor-pointer border-none"
        >
          {isBuilding ? (
            <>
              <div className="w-4 h-4 border-2 border-[#333] border-t-white rounded-full animate-spin" />
              Building Knowledge Graph...
            </>
          ) : (
            <>
              <Network className="w-5 h-5" />
              Build Knowledge Graph
            </>
          )}
        </button>
        {isBuilding && (
          <div className="flex flex-col items-center gap-2">
            <p className="text-sm text-[#555]">Exporting corpus → Running Graphify → Parsing graph...</p>
            <div className="w-72 h-1.5 bg-[#1a1a1a] rounded-full overflow-hidden">
              <div className="h-full bg-[#c8956c] animate-pulse rounded-full" style={{ width: '100%' }} />
            </div>
          </div>
        )}
        {error && (
          <div className="p-3 rounded-lg bg-[#c45a5a]/10 border border-[#c45a5a]/20 text-[#c45a5a] text-sm flex items-center gap-2 max-w-lg">
            <AlertTriangle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        )}
      </div>
    );
  }

  if (error) {
    return (
      <div className="m-4 p-4 rounded-xl bg-[#c45a5a]/10 border border-[#c45a5a]/20 text-[#c45a5a] text-sm">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-4 h-4" />
          <span className="font-semibold">Error</span>
        </div>
        {error}
        <button onClick={loadKg} className="mt-2 px-3 py-1.5 rounded-lg text-xs bg-[#c45a5a]/15 text-[#c45a5a] hover:bg-[#c45a5a]/25 cursor-pointer border-none transition-colors duration-150">
          Retry
        </button>
      </div>
    );
  }

  if (!kg) return null;

  const visibleNodes = kg.nodes.filter((n) => !hiddenCommunities.has(n.community));

  return (
    <div className="flex gap-3 h-[calc(100vh-140px)]">
      {/* Left Sidebar */}
      <div className="w-60 flex-shrink-0 overflow-y-auto">
        <div className="flex flex-col gap-3 pb-6">
          <div className="flex items-center gap-2">
            {kg.graph_html_available && (
              <button
                onClick={() => window.open(api.getGraphHtmlUrl(runId), '_blank')}
                className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-xs bg-[#7dac5a]/10 text-[#7dac5a] hover:bg-[#7dac5a]/20 transition-colors duration-150 cursor-pointer border-none"
              >
                <ExternalLink className="w-3 h-3" />
                Open Interactive
              </button>
            )}
            <button
              onClick={() => setNotBuilt(true)}
              className="p-2 rounded-xl bg-white/[0.03] text-[#555] hover:text-[#999] hover:bg-white/[0.05] transition-colors duration-150 cursor-pointer border-none"
              title="Rebuild knowledge graph"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          <KGStatsPanel kg={kg} onGodNodeClick={handleGodNodeClick} />
          <CommunityLegend
            communities={kg.communities}
            hiddenCommunities={hiddenCommunities}
            onToggleCommunity={handleToggleCommunity}
          />

          {hiddenCommunities.size > 0 && (
            <div className="text-xs text-[#555] text-center">
              {visibleNodes.length} / {kg.nodes.length} nodes visible
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col gap-2">
        {/* Tab bar */}
        <div className="flex items-center justify-between">
          <div className="flex bg-white/[0.03] rounded-xl p-0.5">
            {([
              { id: 'graph' as const, label: 'Graph', icon: Network },
              { id: 'query' as const, label: 'Query', icon: Search },
            ]).map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-150 cursor-pointer border-none ${
                  activeTab === t.id ? 'bg-white/[0.06] text-[#e0e0e0]' : 'text-[#555] hover:text-[#999]'
                }`}
              >
                <t.icon className="w-3.5 h-3.5" />
                {t.label}
              </button>
            ))}
          </div>

          {activeTab === 'graph' && (
            <div className="flex items-center gap-2">
              <button onClick={handleZoomIn} className="p-1.5 rounded-lg bg-white/[0.03] text-[#555] hover:text-[#999] hover:bg-white/[0.05] transition-colors duration-150 cursor-pointer border-none" title="Zoom in">
                <ZoomIn className="w-4 h-4" />
              </button>
              <button onClick={handleZoomOut} className="p-1.5 rounded-lg bg-white/[0.03] text-[#555] hover:text-[#999] hover:bg-white/[0.05] transition-colors duration-150 cursor-pointer border-none" title="Zoom out">
                <ZoomOut className="w-4 h-4" />
              </button>
              <button onClick={handleFit} className="p-1.5 rounded-lg bg-white/[0.03] text-[#555] hover:text-[#999] hover:bg-white/[0.05] transition-colors duration-150 cursor-pointer border-none" title="Fit to view">
                <Focus className="w-4 h-4" />
              </button>
              <div className="flex items-center gap-1.5 ml-2 text-xs text-[#555]">
                <span>Edges:</span>
                <span className="px-1.5 py-0.5 rounded border border-white/[0.06] text-[10px]">━━ Extracted</span>
                <span className="px-1.5 py-0.5 rounded border border-white/[0.06] text-[10px]">╌╌ Inferred</span>
                <span className="px-1.5 py-0.5 rounded border border-white/[0.06] text-[10px]">··· Ambiguous</span>
              </div>
            </div>
          )}
        </div>

        {/* Graph panel */}
        {activeTab === 'graph' && (
          <div className="flex-1 relative">
            <div
              ref={graphRef}
              className="w-full h-full min-h-[500px] rounded-xl border border-[#1e293b] relative"
              style={{ background: '#0f172a' }}
            />

            {/* Node detail popover */}
            {popoverOpened && selectedNode && (
              <div className="absolute top-4 right-4 w-80 liquid-glass-strong rounded-xl p-4 z-10">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {selectedNode.is_god_node && <Crown className="w-4 h-4 text-[#FFD700]" />}
                    <span className="text-sm font-semibold text-[#e0e0e0]">{selectedNode.label}</span>
                  </div>
                  <button onClick={() => setPopoverOpened(false)} className="text-[#555] hover:text-[#999] cursor-pointer bg-transparent border-none">
                    ✕
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5 mb-2">
                  <span className={`inline-flex items-center px-2 py-0.5 text-[10px] rounded-full ${
                    selectedNode.provenance === 'EXTRACTED' ? 'bg-[#7dac5a]/10 text-[#7dac5a] border border-[#7dac5a]/20' :
                    selectedNode.provenance === 'INFERRED' ? 'bg-[#e0af68]/10 text-[#e0af68] border border-[#e0af68]/20' :
                    'bg-[#c45a5a]/10 text-[#c45a5a] border border-[#c45a5a]/20'
                  }`}>
                    {selectedNode.provenance}
                  </span>
                  <span className="inline-flex items-center px-2 py-0.5 text-[10px] rounded-full bg-white/[0.03] text-[#555] border border-white/[0.06]">
                    {selectedNode.degree} edges
                  </span>
                  <span className="inline-flex items-center px-2 py-0.5 text-[10px] rounded-full bg-white/[0.03] text-[#555] border border-white/[0.06]">
                    Community {selectedNode.community}
                  </span>
                </div>
                {selectedNode.confidence < 1 && (
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs text-[#555]">Confidence:</span>
                    <div className="flex-1 h-1.5 bg-[#1a1a1a] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${selectedNode.confidence * 100}%`,
                          backgroundColor: selectedNode.confidence > 0.7 ? '#7dac5a' : '#e0af68',
                        }}
                      />
                    </div>
                    <span className="text-xs text-[#555]">{(selectedNode.confidence * 100).toFixed(0)}%</span>
                  </div>
                )}
                {selectedNode.summary && (
                  <div className="border-t border-white/[0.06] pt-2 mb-2">
                    <p className="text-xs text-[#999] leading-relaxed">
                      {selectedNode.summary.length > 200 ? selectedNode.summary.slice(0, 200) + '…' : selectedNode.summary}
                    </p>
                  </div>
                )}
                {selectedNode.file_path && (
                  <div className="flex items-center justify-between gap-2 pt-2 border-t border-white/[0.06]">
                    <span className="text-xs text-[#555] font-mono break-all flex-1">{selectedNode.file_path}</span>
                    <button
                      onClick={async () => {
                        if (selectedNode.file_path) {
                          try { await api.openFile(selectedNode.file_path); }
                          catch (err) { alert(`Failed to open file: ${err instanceof Error ? err.message : String(err)}`); }
                        }
                      }}
                      className="p-1.5 rounded-lg bg-white/[0.03] text-[#555] hover:text-[#999] hover:bg-white/[0.05] transition-colors duration-150 cursor-pointer border-none"
                      title="Open in local editor"
                    >
                      <FileCode className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Query panel */}
        {activeTab === 'query' && <KGQueryPanel runId={runId} />}
      </div>
    </div>
  );
}
