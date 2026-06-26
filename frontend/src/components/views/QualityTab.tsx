import { useState, useEffect } from 'react';
import { getQualityReport } from '../../api/client';
import type { QualityReport } from '../../types/api';

interface Props {
  runId: string;
}

export default function QualityTab({ runId }: Props) {
  const [report, setReport] = useState<QualityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getQualityReport(runId)
      .then((data: QualityReport) => {
        setReport(data);
        setError(null);
      })
      .catch((err: Error) => {
        setError(err.message || 'Failed to load quality report');
      })
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 text-gray-400">
        <span className="animate-pulse">Analyzing report quality...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-red-400 border border-red-900/30 rounded-lg">
        {error}
      </div>
    );
  }

  if (!report) return null;

  const scores = [
    { label: 'Confidence', value: report.confidence_score },
    { label: 'Citations', value: report.citation_verification_rate },
    { label: 'Diversity', value: report.source_diversity_score },
    { label: 'Completeness', value: report.completeness_score },
    { label: 'Coherence', value: report.coherence_score },
  ];

  const overall = report.overall_score;
  const overallColor =
    overall >= 0.8 ? 'text-green-400' : overall >= 0.6 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="space-y-6">
      {/* Overall Score */}
      <div className="liquid-glass rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-white">Overall Quality</h3>
            <p className="text-sm text-gray-400 mt-1">
              Based on {scores.length} dimensions
            </p>
          </div>
          <div className={`text-4xl font-bold ${overallColor}`}>
            {Math.round(overall * 100)}%
          </div>
        </div>
      </div>

      {/* Score Bars */}
      <div className="liquid-glass rounded-lg p-6 space-y-4">
        <h3 className="text-sm font-medium text-gray-300 uppercase tracking-wider">
          Dimension Scores
        </h3>
        {scores.map((s) => (
          <div key={s.label} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-gray-300">{s.label}</span>
              <span className="text-gray-400">{Math.round(s.value * 100)}%</span>
            </div>
            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${s.value * 100}%`,
                  backgroundColor:
                    s.value >= 0.8 ? '#4ade80' : s.value >= 0.6 ? '#facc15' : '#f87171',
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Suggestions */}
      {report.improvement_suggestions.length > 0 && (
        <div className="liquid-glass rounded-lg p-6">
          <h3 className="text-sm font-medium text-gray-300 uppercase tracking-wider mb-3">
            Suggestions
          </h3>
          <ul className="space-y-2">
            {report.improvement_suggestions.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                <span className="text-amber-400 mt-0.5">→</span>
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
