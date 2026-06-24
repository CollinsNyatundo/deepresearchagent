/**
 * KGStatsPanel — Compact stats bar for the knowledge graph.
 */

import { Network, GitBranch, Crown, Zap, Sparkles } from 'lucide-react';
import type { KnowledgeGraph } from '../../types/api';

interface KGStatsPanelProps {
  kg: KnowledgeGraph;
  onGodNodeClick?: (nodeId: string) => void;
}

export function KGStatsPanel({ kg, onGodNodeClick }: KGStatsPanelProps) {
  const compressionPercent = kg.compression_ratio > 0
    ? Math.min(Math.round((1 - 1 / kg.compression_ratio) * 100), 99)
    : 0;

  return (
    <div className="flex flex-col gap-3">
      {/* Node / Edge / Community counts */}
      <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
        <h6 className="text-[10px] uppercase tracking-wider text-[#555] font-semibold mb-3">Graph Statistics</h6>
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-[#4F46E5]/10 flex items-center justify-center">
                <Network className="w-3 h-3 text-[#4F46E5]" />
              </div>
              <span className="text-xs text-[#555]">Nodes</span>
            </div>
            <span className="px-2 py-0.5 text-xs rounded-full bg-[#4F46E5]/10 text-[#4F46E5] font-mono">
              {kg.nodes.length.toLocaleString()}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-[#7C3AED]/10 flex items-center justify-center">
                <GitBranch className="w-3 h-3 text-[#7C3AED]" />
              </div>
              <span className="text-xs text-[#555]">Edges</span>
            </div>
            <span className="px-2 py-0.5 text-xs rounded-full bg-[#7C3AED]/10 text-[#7C3AED] font-mono">
              {kg.edges.length.toLocaleString()}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-[#059669]/10 flex items-center justify-center">
                <Sparkles className="w-3 h-3 text-[#059669]" />
              </div>
              <span className="text-xs text-[#555]">Communities</span>
            </div>
            <span className="px-2 py-0.5 text-xs rounded-full bg-[#059669]/10 text-[#059669] font-mono">
              {kg.communities.length}
            </span>
          </div>
        </div>
      </div>

      {/* Token compression */}
      {kg.compression_ratio > 1 && (
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-[#D97706]/10 flex items-center justify-center">
                <Zap className="w-3 h-3 text-[#D97706]" />
              </div>
              <span className="text-xs text-[#555]">Token Efficiency</span>
            </div>
            <span
              className="px-2 py-0.5 text-xs rounded-full bg-[#D97706]/10 text-[#D97706] font-mono cursor-help"
              title={`Graph queries use ~${kg.graph_token_cost.toLocaleString()} tokens vs ~${kg.naive_token_cost.toLocaleString()} for raw read`}
            >
              {kg.compression_ratio.toFixed(1)}× compression
            </span>
          </div>
          <div className="w-full h-1.5 bg-[#1a1a1a] rounded-full overflow-hidden">
            <div className="h-full bg-[#D97706] rounded-full" style={{ width: `${compressionPercent}%` }} />
          </div>
          <p className="text-xs text-[#555] mt-1">{compressionPercent}% token savings vs reading raw files</p>
        </div>
      )}

      {/* God nodes */}
      {kg.god_nodes.length > 0 && (
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
          <div className="flex items-center gap-2 mb-2">
            <Crown className="w-4 h-4 text-[#FFD700]" />
            <h6 className="text-[10px] uppercase tracking-wider text-[#555] font-semibold">God Nodes</h6>
          </div>
          <div className="flex flex-col gap-1">
            {kg.god_nodes.slice(0, 7).map((nodeId) => {
              const node = kg.nodes.find((n) => n.id === nodeId);
              const label = node?.label || nodeId;
              return (
                <div key={nodeId} className="flex items-center justify-between">
                  <button
                    onClick={() => onGodNodeClick?.(nodeId)}
                    className="text-xs text-[#d4a574] hover:text-[#c8956c] hover:underline cursor-pointer bg-transparent border-none text-left truncate max-w-[140px]"
                  >
                    {label.length > 28 ? `${label.slice(0, 28)}…` : label}
                  </button>
                  <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-white/[0.03] text-[#555] border border-white/[0.06]">
                    {node?.degree ?? '?'} edges
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Surprise edges */}
      {kg.surprise_edges.length > 0 && (
        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-[#7C3AED]" />
            <h6 className="text-[10px] uppercase tracking-wider text-[#555] font-semibold">Surprise Connections</h6>
          </div>
          <div className="flex flex-col gap-2">
            {kg.surprise_edges.slice(0, 5).map((edge, i) => {
              const srcNode = kg.nodes.find((n) => n.id === edge.source);
              const tgtNode = kg.nodes.find((n) => n.id === edge.target);
              const srcLabel = srcNode?.label || edge.source;
              const tgtLabel = tgtNode?.label || edge.target;

              return (
                <div key={i} className="pb-2 border-b border-white/[0.06] last:border-0 last:pb-0">
                  <div className="flex items-center gap-1 mb-1">
                    <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-[#7C3AED]/10 text-[#7C3AED] border border-[#7C3AED]/20">
                      {srcLabel.length > 16 ? `${srcLabel.slice(0, 16)}…` : srcLabel}
                    </span>
                    <span className="text-xs text-[#555]">↔</span>
                    <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-[#7C3AED]/10 text-[#7C3AED] border border-[#7C3AED]/20">
                      {tgtLabel.length > 16 ? `${tgtLabel.slice(0, 16)}…` : tgtLabel}
                    </span>
                  </div>
                  <p className="text-xs text-[#555] ml-1">
                    {edge.reason.length > 80 ? `${edge.reason.slice(0, 80)}…` : edge.reason}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
