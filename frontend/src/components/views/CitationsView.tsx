import { useEffect, useState, useRef } from 'react';
import { Link, Quote } from 'lucide-react';
import { api } from '../../api/client';
import type { ResearchResult } from '../../types/api';

type Props = {
  runId: string;
};

export function CitationsView({ runId }: Props) {
  const [runDetails, setRunDetails] = useState<ResearchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [highlightedId, setHighlightedId] = useState<string | null>(null);
  
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const fetchDetails = () => {
    setLoading(true);
    api
      .getRunDetails(runId)
      .then((details) => {
        setRunDetails(details);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDetails();

    const handleResynthesisComplete = (e: Event) => {
      const customEvent = e as CustomEvent<{ runId: string }>;
      if (customEvent.detail.runId === runId) {
        fetchDetails();
      }
    };

    window.addEventListener('resynthesis-complete', handleResynthesisComplete);
    return () => {
      window.removeEventListener('resynthesis-complete', handleResynthesisComplete);
    };
  }, [runId]);

  useEffect(() => {
    const handleHighlight = (e: Event) => {
      const customEvent = e as CustomEvent<{ url?: string; id?: string }>;
      const { id } = customEvent.detail;
      if (id) {
        const normalizedId = id.startsWith('c') ? id : `c${id}`;
        setHighlightedId(normalizedId);
        
        const cardEl = cardRefs.current[normalizedId];
        if (cardEl) {
          cardEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }
    };

    const handleClearHighlight = () => {
      setHighlightedId(null);
    };

    window.addEventListener('highlight-citation', handleHighlight);
    window.addEventListener('clear-highlight-citation', handleClearHighlight);

    return () => {
      window.removeEventListener('highlight-citation', handleHighlight);
      window.removeEventListener('clear-highlight-citation', handleClearHighlight);
    };
  }, []);

  const handleMouseEnterCard = (id: string) => {
    const event = new CustomEvent('highlight-citation-in-report', { detail: { id } });
    window.dispatchEvent(event);
  };

  const handleMouseLeaveCard = () => {
    const event = new CustomEvent('clear-highlight-citation-in-report');
    window.dispatchEvent(event);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-2 border-[#c8956c] border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-[#999]">Compiling sources…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-24">
        <span className="text-sm text-[#c45a5a]">Failed to load citations: {error}</span>
      </div>
    );
  }

  const citations = runDetails?.citations || [];

  if (citations.length === 0) {
    return (
      <div className="flex items-center justify-center py-24">
        <span className="text-sm text-[#999]">No citations found for this research run.</span>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto custom-scrollbar" style={{ height: 'calc(100vh - 180px)' }}>
      <div className="flex flex-col gap-4 pr-4 pb-8">
        <div>
          <h2 className="text-lg font-bold" style={{ fontFamily: 'Fira Sans' }}>
            Compiled Citations & Sources
          </h2>
          <span className="text-xs text-[#999] mt-0.5 block">
            Total unique references crawled: {citations.length}
          </span>
        </div>

        {citations.map((citation, index) => {
          const citeId = citation.id.startsWith('c') ? citation.id : `c${citation.id}`;
          const isHighlighted = highlightedId === citeId;
          const displayIdx = citation.id.replace(/^c/, '') || String(index + 1);

          return (
            <div
              key={citation.id}
              ref={(el) => { cardRefs.current[citeId] = el; }}
              id={`citation-card-${citeId}`}
              className="p-4 rounded-xl border border-white/[0.06] bg-white/[0.03] transition-all duration-200"
              onMouseEnter={() => handleMouseEnterCard(citeId)}
              onMouseLeave={handleMouseLeaveCard}
              style={{
                borderColor: isHighlighted ? '#c8956c' : undefined,
                boxShadow: isHighlighted ? '0 0 12px rgba(200, 149, 108, 0.25)' : undefined,
                transform: isHighlighted ? 'scale(1.01)' : undefined,
              }}
            >
              <div className="flex flex-col gap-1.5">
                {/* Header row */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2 flex-1 min-w-0">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-mono font-bold flex-shrink-0"
                      style={{
                        backgroundColor: isHighlighted ? 'rgba(200, 149, 108, 0.15)' : 'rgba(125, 172, 90, 0.1)',
                        color: isHighlighted ? '#c8956c' : '#7dac5a',
                      }}
                    >
                      {displayIdx}
                    </div>
                    <a
                      href={citation.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-semibold hover:underline transition-colors duration-150"
                      style={{ fontFamily: 'Fira Sans', color: '#e0e0e0', lineHeight: 1.4 }}
                    >
                      {citation.title || 'Source Reference'}
                    </a>
                  </div>

                  {citation.domain && (
                    <span className="px-2 py-0.5 text-[10px] rounded-full border border-[#555] text-[#999] flex-shrink-0">
                      {citation.domain}
                    </span>
                  )}
                </div>

                {/* Snippet block */}
                {citation.snippet && (
                  <div className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                    <div className="flex items-start gap-2">
                      <Quote size={14} className="text-[#7dac5a] flex-shrink-0 mt-0.5" />
                      <span className="text-xs text-[#999]" style={{ fontFamily: 'Fira Sans', lineHeight: 1.6 }}>
                        {citation.snippet}
                      </span>
                    </div>
                  </div>
                )}

                {/* Link row */}
                <div className="flex items-center justify-between mt-1 gap-2">
                  <a
                    href={citation.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] truncate hover:text-[#d4a574] transition-colors duration-150"
                    style={{ fontFamily: 'Fira Code', color: '#7dac5a', maxWidth: '85%' }}
                  >
                    <Link size={10} className="inline align-middle mr-1" />
                    {citation.url}
                  </a>
                  
                  {citation.accessed_at && (
                    <span className="text-[10px] text-[#999]">
                      Accessed {new Date(citation.accessed_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
