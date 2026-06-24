/**
 * KGQueryPanel — Strategy B: Query the knowledge graph via MCP bridge.
 */

import { useState } from 'react';
import {
  Search, GitBranch, Zap, AlertTriangle, Check
} from 'lucide-react';
import { api } from '../../api/client';
import type { KGQueryResult } from '../../types/api';

interface KGQueryPanelProps {
  runId: string;
}

export function KGQueryPanel({ runId }: KGQueryPanelProps) {
  const [question, setQuestion] = useState('');
  const [mode, setMode] = useState<'bfs' | 'dfs'>('bfs');
  const [budget, setBudget] = useState<number>(2000);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<KGQueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleQuery = async () => {
    if (!question.trim()) return;
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.queryKnowledgeGraph(runId, {
        question: question.trim(), mode, budget,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-full bg-[#4F46E5]/10 flex items-center justify-center">
          <Search className="w-4 h-4 text-[#4F46E5]" />
        </div>
        <h5 className="text-base font-bold text-[#e0e0e0]">Graph Query (MCP Bridge)</h5>
      </div>

      <div className="flex flex-col gap-3">
        <textarea
          placeholder="What connects topic A to topic B? What are the central concepts? How does X relate to Y?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:outline-none focus:border-[#c8956c]/50 resize-y min-h-[60px]"
        />
        <p className="text-xs text-[#555]">
          Ask a natural language question — the graph traversal engine answers using indexed relationships instead of raw text.
        </p>

        <div className="flex items-end gap-4 flex-wrap">
          <div>
            <label className="block text-xs uppercase tracking-wider text-[#555] font-semibold mb-2">Traversal Mode</label>
            <div className="flex bg-white/[0.03] rounded-xl p-0.5">
              {([
                { label: 'BFS (breadth-first)', value: 'bfs' as const },
                { label: 'DFS (depth-first)', value: 'dfs' as const },
              ]).map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setMode(opt.value)}
                  className={`px-3 py-1.5 text-xs rounded-lg transition-all duration-150 cursor-pointer border-none ${
                    mode === opt.value ? 'bg-white/[0.06] text-[#e0e0e0]' : 'text-[#555] hover:text-[#999]'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs uppercase tracking-wider text-[#555] font-semibold mb-2">Token Budget</label>
            <input
              type="number"
              min={500} max={8000} step={500}
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value) || 2000)}
              className="w-32 bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 text-sm text-[#e0e0e0] focus:outline-none focus:border-[#c8956c]/50"
            />
            <p className="text-xs text-[#555] mt-1">Max tokens for answer</p>
          </div>

          <button
            onClick={handleQuery}
            disabled={!question.trim() || isLoading}
            className="flex items-center gap-2 py-2.5 px-4 rounded-xl text-sm font-medium bg-[#c8956c]/15 text-[#c8956c] hover:bg-[#c8956c]/25 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150 cursor-pointer border-none"
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-[#333] border-t-white rounded-full animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            Query Graph
          </button>
        </div>

        {/* Mode hints */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-full bg-[#4F46E5]/10 text-[#4F46E5] border border-[#4F46E5]/20">
            BFS — best for concept exploration, "what relates to X"
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-full bg-[#7C3AED]/10 text-[#7C3AED] border border-[#7C3AED]/20">
            DFS — best for path tracing, "how does X connect to Y"
          </span>
        </div>

        {/* Error */}
        {error && (
          <div className="p-3 rounded-lg bg-[#c45a5a]/10 border border-[#c45a5a]/20 text-[#c45a5a] text-sm flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-auto text-[#c45a5a] hover:text-[#e0e0e0] cursor-pointer bg-transparent border-none">✕</button>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="border-t border-white/[0.06] pt-4 flex flex-col gap-3">
            <div className="bg-white/[0.03] rounded-xl p-4">
              <p className="text-sm text-[#e0e0e0] whitespace-pre-wrap leading-relaxed">{result.answer}</p>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-full bg-[#7dac5a]/10 text-[#7dac5a] border border-[#7dac5a]/20">
                <Check className="w-3 h-3" />
                {result.query_mode.toUpperCase()} traversal
              </span>
              {result.nodes_traversed.length > 0 && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-full bg-[#4F46E5]/10 text-[#4F46E5] border border-[#4F46E5]/20">
                  <GitBranch className="w-3 h-3" />
                  {result.nodes_traversed.length} nodes traversed
                </span>
              )}
              {result.token_cost > 0 && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-full bg-[#D97706]/10 text-[#D97706] border border-[#D97706]/20">
                  <Zap className="w-3 h-3" />
                  {result.token_cost.toLocaleString()} tokens
                </span>
              )}
            </div>

            {result.nodes_traversed.length > 0 && (
              <details>
                <summary className="text-xs text-[#555] cursor-pointer">Show traversal path ({result.nodes_traversed.length} nodes)</summary>
                <div className="mt-2 p-3 rounded-lg bg-black font-mono text-[11px] text-[#999] max-h-32 overflow-y-auto">
                  {result.nodes_traversed.join(' → ')}
                </div>
              </details>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
