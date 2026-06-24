import { ZoomIn, ExternalLink, Quote } from 'lucide-react';
import type { MindmapNode, CitationRef } from '../../types/api';

type Props = {
  node: MindmapNode;
  onDrillDeeper: (nodeId: string) => void;
  loading: boolean;
};

const TYPE_CONFIG: Record<string, { color: string; label: string }> = {
  root: { color: 'indigo', label: 'Root' },
  section: { color: 'teal', label: 'Section' },
  detail: { color: 'blue', label: 'Detail' },
};

const badgeColorMap: Record<string, { bg: string; text: string }> = {
  indigo: { bg: 'bg-[#c8956c]/20', text: 'text-[#c8956c]' },
  teal: { bg: 'bg-[#7dac5a]/20', text: 'text-[#7dac5a]' },
  blue: { bg: 'bg-[#d4a574]/20', text: 'text-[#d4a574]' },
};

export function NodeDetailsPanel({ node, onDrillDeeper, loading }: Props) {
  const typeConf = TYPE_CONFIG[node.type] || TYPE_CONFIG.detail;

  // Normalize citations — can be strings or CitationRef objects
  const citations: CitationRef[] = (node.citations || []).map((c, _i) => {
    if (typeof c === 'string') {
      return { id: c, url: '#', title: c };
    }
    return c as CitationRef;
  });

  return (
    <div className="w-[360px] h-full overflow-y-auto border-l border-[#1a1a1a] bg-black flex flex-col p-6 custom-scrollbar">
      <div className="flex flex-col gap-4">
        {/* Header */}
        <div className="flex justify-between items-start flex-nowrap">
          <h4 className="flex-1 text-lg font-semibold text-[#e0e0e0]">
            {node.label}
          </h4>
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${badgeColorMap[typeConf.color]?.bg || 'bg-white/[0.03]'} ${badgeColorMap[typeConf.color]?.text || 'text-[#999]'}`}>
            {typeConf.label}
          </span>
        </div>

        {/* Summary */}
        {node.summary && (
          <>
            <div className="border-t border-[#1a1a1a]" />
            <p className="text-sm text-[#999] leading-relaxed">
              {node.summary}
            </p>
          </>
        )}

        {/* Citations */}
        {citations.length > 0 && (
          <>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 shrink-0">
                <Quote size={14} className="text-[#999]" />
                <span className="text-xs text-[#999]">Citations ({citations.length})</span>
              </div>
              <div className="flex-1 h-px bg-[#1a1a1a]" />
            </div>
            <div className="flex flex-col gap-1">
              {citations.map((cit, i) => (
                <a
                  key={i}
                  href={cit.url !== '#' ? cit.url : undefined}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-sm px-2 py-1 rounded bg-white/[0.03] hover:bg-white/[0.06] transition-colors duration-150"
                >
                  <ExternalLink size={14} className="flex-shrink-0 text-[#999]" />
                  <span className="text-xs text-[#e0e0e0] truncate">
                    {cit.title || cit.url}
                  </span>
                </a>
              ))}
            </div>
          </>
        )}

        {/* Drill Deeper */}
        <div className="border-t border-[#1a1a1a]" />
        <button
          className="inline-flex items-center justify-center gap-2 w-full rounded-xl bg-[#c8956c]/15 hover:bg-[#c8956c]/25 text-[#c8956c] px-4 py-2.5 text-sm font-medium transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={() => onDrillDeeper(node.id)}
          disabled={loading}
        >
          {loading ? (
            <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <ZoomIn size={18} />
          )}
          {loading ? 'Expanding…' : 'Drill Deeper'}
        </button>
      </div>
    </div>
  );
}
