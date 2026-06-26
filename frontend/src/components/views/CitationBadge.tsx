import { useState, useEffect, useRef } from 'react';
import { verifyCitation } from '../../api/client';
import type { CitationStatus, CitationVerificationResponse } from '../../types/api';

interface Props {
  citationText: string;
  _runId?: string;
}

export default function CitationBadge({ citationText }: Props) {
  const [status, setStatus] = useState<CitationStatus | 'loading'>('loading');
  const [confidence, setConfidence] = useState<number>(0);
  const badgeRef = useRef<HTMLSpanElement>(null);
  const hasLoaded = useRef(false);

  useEffect(() => {
    if (!badgeRef.current || hasLoaded.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !hasLoaded.current) {
          hasLoaded.current = true;
          verifyCitation({ citation_text: citationText })
            .then((result: CitationVerificationResponse) => {
              setStatus(result.status);
              setConfidence(result.confidence);
            })
            .catch(() => {
              setStatus('failed');
              setConfidence(0);
            })
            .finally(() => observer.disconnect());
        }
      },
      { rootMargin: '50px' }
    );

    observer.observe(badgeRef.current);
    return () => observer.disconnect();
  }, [citationText]);

  const icons: Record<string, string> = {
    loading: '⏳',
    verified: '✅',
    unverified: '⚠️',
    failed: '❌',
  };

  const labels: Record<string, string> = {
    loading: 'Verifying citation...',
    verified: `Verified citation (${Math.round(confidence * 100)}% confidence)`,
    unverified: `Unverified citation (${Math.round(confidence * 100)}% confidence)`,
    failed: 'Failed verification',
  };

  const colors: Record<string, string> = {
    loading: 'text-gray-400',
    verified: 'text-green-400',
    unverified: 'text-yellow-400',
    failed: 'text-red-400',
  };

  return (
    <span
      ref={badgeRef}
      className={`inline-flex items-center gap-1 text-xs ${colors[status] || colors.loading} cursor-help`}
      aria-label={labels[status] || labels.loading}
      title={labels[status] || labels.loading}
    >
      {icons[status] || icons.loading}
      {status !== 'loading' && (
        <span className="sr-only">{labels[status]}</span>
      )}
    </span>
  );
}
