import { useEffect, useState } from 'react';
import { FileText, Clock, Download } from 'lucide-react';
import { api } from '../../api/client';
import type { RunSummary } from '../../types/api';
import { useVirtualList } from '../../hooks/useVirtualList';

type Props = {
  selectedRunId: string | null;
  onSelectRun: (id: string) => void;
  selectedWorkspaceId: string | null;
};

function useExportStatus(runs: RunSummary[]) {
  const [statusMap, setStatusMap] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (runs.length === 0) return;
    runs.forEach((run) => {
      api
        .listExports(run.id)
        .then(({ formats }) => {
          const hasCached = formats.some((f) => f.cached);
          setStatusMap((prev) => ({ ...prev, [run.id]: hasCached }));
        })
        .catch(() => {});
    });
  }, [runs]);

  return statusMap;
}

export function RunList({ selectedRunId, onSelectRun, selectedWorkspaceId }: Props) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedWorkspaceId) {
      setRuns([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    api
      .listRuns(selectedWorkspaceId)
      .then(setRuns)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedWorkspaceId]);

  const exportStatus = useExportStatus(runs);

  const { containerRef, visibleItems, totalHeight, offsetY, onScroll } = useVirtualList(runs, { itemHeight: 72 });

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-8 gap-2">
        <div className="w-5 h-5 border-2 border-[#333] border-t-[#c8956c] rounded-full animate-spin" />
        <span className="text-xs text-[#555]">Loading runs…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-4 text-sm text-[#c45a5a]">
        Failed to load runs. Is the API server running?
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="flex flex-col items-center py-8 gap-2">
        <FileText className="w-8 h-8 text-[#333]" />
        <span className="text-sm text-[#555] text-center">No research runs yet.</span>
        <span className="text-xs text-[#555] text-center">Click "New Research" to get started.</span>
      </div>
    );
  }

  return (
    <div ref={containerRef} onScroll={onScroll} className="flex-1 overflow-y-auto">
      <div style={{ height: totalHeight, position: 'relative' }}>
        <div style={{ transform: `translateY(${offsetY}px)` }} className="flex flex-col gap-1">
          {visibleItems.map((run) => (
            <button
              key={run.id}
              onClick={() => onSelectRun(run.id)}
              className={`text-left w-full px-3 py-2 rounded-xl transition-all duration-150 cursor-pointer border-none flex flex-col gap-1 ${
                run.id === selectedRunId
                  ? 'bg-white/[0.06]'
                  : 'hover:bg-white/[0.03]'
              }`}
            >
              <div className="flex items-start gap-2">
                <FileText className="w-4 h-4 text-[#555] shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <span className={`text-sm line-clamp-2 ${run.id === selectedRunId ? 'font-semibold text-[#e0e0e0]' : 'text-[#999]'}`}>
                    {run.query}
                  </span>
                  <div className="flex items-center gap-1 mt-1">
                    <Clock className="w-3 h-3 text-[#555]" />
                    <span className="text-xs text-[#555]">{formatDate(run.created_at)}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1.5 flex-wrap ml-6">
                {exportStatus[run.id] && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-full bg-[#7dac5a]/10 text-[#7dac5a] border border-[#7dac5a]/20">
                    <Download className="w-3 h-3" />
                    DL
                  </span>
                )}
                {run.model_used && (
                  <span className="inline-flex items-center px-2 py-0.5 text-[10px] rounded-full bg-white/[0.03] text-[#555] border border-white/[0.06]">
                    {run.model_used.split('/').pop()?.replace(/:.*$/, '').slice(0, 12) || ''}
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch {
    return dateStr;
  }
}
