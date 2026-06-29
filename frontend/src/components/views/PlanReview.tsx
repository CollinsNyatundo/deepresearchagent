import { useState } from 'react';
import { Plus, Trash2, Pencil, Check, X, Play, RefreshCw, Clock, Route } from 'lucide-react';
import type { PlanPreview } from '../../types/api';

type Props = {
  preview: PlanPreview;
  query: string;
  onApprove: (
    steps: string[],
    subQueries: string[],
    exportFormats: string[],
  ) => void;
  onRegenerate: () => void;
  isLoading?: boolean;
};

export function PlanReview({
  preview,
  query,
  onApprove,
  onRegenerate,
  isLoading = false,
}: Props) {
  const [steps, setSteps] = useState<string[]>([...preview.plan.steps]);
  const [subQueries, setSubQueries] = useState<string[]>([
    ...preview.sub_queries,
  ]);
  const [exportFormats, setExportFormats] = useState<string[]>([
    'markdown',
    'pdf',
  ]);
  const [editingStep, setEditingStep] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');
  const [editingQuery, setEditingQuery] = useState<number | null>(null);
  const [queryEditValue, setQueryEditValue] = useState('');
  const [newStepValue, setNewStepValue] = useState('');

  const handleEditStep = (idx: number) => {
    setEditingStep(idx);
    setEditValue(steps[idx]);
  };

  const handleSaveStep = () => {
    if (editingStep !== null && editValue.trim()) {
      const newSteps = [...steps];
      newSteps[editingStep] = editValue.trim();
      setSteps(newSteps);
    }
    setEditingStep(null);
    setEditValue('');
  };

  const handleDeleteStep = (idx: number) => {
    setSteps(steps.filter((_, i) => i !== idx));
  };

  const handleAddStep = () => {
    if (newStepValue.trim()) {
      setSteps([...steps, newStepValue.trim()]);
      setNewStepValue('');
    }
  };

  const handleEditQuery = (idx: number) => {
    setEditingQuery(idx);
    setQueryEditValue(subQueries[idx]);
  };

  const handleSaveQuery = () => {
    if (editingQuery !== null && queryEditValue.trim()) {
      const newQueries = [...subQueries];
      newQueries[editingQuery] = queryEditValue.trim();
      setSubQueries(newQueries);
    }
    setEditingQuery(null);
    setQueryEditValue('');
  };

  const handleDeleteQuery = (idx: number) => {
    setSubQueries(subQueries.filter((_, i) => i !== idx));
  };

  const toggleFormat = (format: string) => {
    setExportFormats((prev) =>
      prev.includes(format)
        ? prev.filter((f) => f !== format)
        : [...prev, format],
    );
  };

  const allFormats = [
    { id: 'markdown', label: 'Markdown (.md)', emoji: '📝' },
    { id: 'pdf', label: 'PDF (.pdf)', emoji: '📕' },
    { id: 'docx', label: 'Word (.docx)', emoji: '📘' },
    { id: 'xlsx', label: 'Excel (.xlsx)', emoji: '📊' },
    { id: 'mindmap_json', label: 'Mindmap (.json)', emoji: '🧠' },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-6 md:p-8 max-w-4xl mx-auto w-full flex flex-col gap-6">
      {/* ─── Header ──────────────────────────────────────────── */}
      <div className="liquid-glass p-6 rounded-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h4 className="text-xl font-bold" style={{ fontFamily: 'Fira Sans' }}>Research Plan Review</h4>
            <p className="text-sm text-[#999] mt-1">
              Review and customize the research plan before execution.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs bg-[#3b82f6]/15 text-[#3b82f6]">
              <Clock size={12} />
              ~{Math.round(preview.estimated_duration_minutes)} min
            </span>
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs bg-[#8b5cf6]/15 text-[#8b5cf6]">
              <Route size={12} />
              {preview.estimated_cycles} cycles
            </span>
          </div>
        </div>

        <div className="mt-4 p-4 rounded-xl bg-[#3b82f6]/10 border border-[#3b82f6]/20 text-sm text-[#e0e0e0]">
          <strong>Query:</strong> {query}
        </div>
      </div>

      {/* ─── Research Steps ──────────────────────────────────── */}
      <div className="liquid-glass p-6 rounded-xl">
        <h5 className="text-lg font-bold mb-4" style={{ fontFamily: 'Fira Sans' }}>
          📋 Research Steps ({steps.length})
        </h5>

        <div className="flex flex-col gap-2">
          {steps.map((step, idx) => (
            <div
              key={idx}
              className="p-3 rounded-lg border border-white/[0.06] bg-white/[0.03] transition-colors"
              style={{
                borderColor: editingStep === idx ? '#6366f1' : undefined,
              }}
            >
              {editingStep === idx ? (
                <div className="flex items-center gap-2">
                  <input
                    value={editValue}
                    onChange={(e) => setEditValue(e.currentTarget.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSaveStep()}
                    className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:border-[#c8956c]/50 focus:outline-none transition-colors"
                    autoFocus
                  />
                  <button
                    className="w-8 h-8 rounded-lg flex items-center justify-center bg-[#7dac5a]/15 hover:bg-[#7dac5a]/25 text-[#7dac5a] transition-colors"
                    onClick={handleSaveStep}
                  >
                    <Check size={16} />
                  </button>
                  <button
                    className="w-8 h-8 rounded-lg flex items-center justify-center bg-[#555]/15 hover:bg-[#555]/25 text-[#999] transition-colors"
                    onClick={() => setEditingStep(null)}
                  >
                    <X size={16} />
                  </button>
                </div>
              ) : (
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="w-6 h-6 rounded-full bg-[#6366f1]/15 flex items-center justify-center flex-shrink-0">
                      <span className="text-xs font-bold text-[#6366f1]">{idx + 1}</span>
                    </div>
                    <span className="text-sm text-[#e0e0e0] truncate">{step}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-white/[0.06] text-[#3b82f6] transition-colors"
                      onClick={() => handleEditStep(idx)}
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-white/[0.06] text-[#c45a5a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      onClick={() => handleDeleteStep(idx)}
                      disabled={steps.length <= 1}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Add new step */}
          <div className="flex items-center gap-2">
            <input
              placeholder="Add a new research step..."
              value={newStepValue}
              onChange={(e) => setNewStepValue(e.currentTarget.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddStep()}
              className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:border-[#c8956c]/50 focus:outline-none transition-colors"
            />
            <button
              className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[#c8956c]/15 hover:bg-[#c8956c]/25 text-[#c8956c] text-sm transition-colors duration-150 disabled:opacity-50"
              onClick={handleAddStep}
              disabled={!newStepValue.trim()}
            >
              <Plus size={14} />
              Add
            </button>
          </div>
        </div>
      </div>

      {/* ─── Sub-Queries ─────────────────────────────────────── */}
      {subQueries.length > 0 && (
        <div className="liquid-glass p-6 rounded-xl">
          <h5 className="text-lg font-bold mb-4" style={{ fontFamily: 'Fira Sans' }}>
            🔍 Search Sub-Queries ({subQueries.length})
          </h5>

          <div className="flex flex-col gap-2">
            {subQueries.map((sq, idx) => (
              <div key={idx} className="p-3 rounded-lg border border-white/[0.06] bg-white/[0.03]">
                {editingQuery === idx ? (
                  <div className="flex items-center gap-2">
                    <input
                      value={queryEditValue}
                      onChange={(e) =>
                        setQueryEditValue(e.currentTarget.value)
                      }
                      onKeyDown={(e) =>
                        e.key === 'Enter' && handleSaveQuery()
                      }
                      className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:border-[#c8956c]/50 focus:outline-none transition-colors"
                      autoFocus
                    />
                    <button
                      className="w-8 h-8 rounded-lg flex items-center justify-center bg-[#7dac5a]/15 hover:bg-[#7dac5a]/25 text-[#7dac5a] transition-colors"
                      onClick={handleSaveQuery}
                    >
                      <Check size={16} />
                    </button>
                    <button
                      className="w-8 h-8 rounded-lg flex items-center justify-center bg-[#555]/15 hover:bg-[#555]/25 text-[#999] transition-colors"
                      onClick={() => setEditingQuery(null)}
                    >
                      <X size={16} />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm text-[#e0e0e0] truncate">{sq}</span>
                    <div className="flex items-center gap-1">
                      <button
                        className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-white/[0.06] text-[#3b82f6] transition-colors"
                        onClick={() => handleEditQuery(idx)}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-white/[0.06] text-[#c45a5a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={() => handleDeleteQuery(idx)}
                        disabled={subQueries.length <= 1}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Export Formats ───────────────────────────────────── */}
      <div className="liquid-glass p-6 rounded-xl">
        <h5 className="text-lg font-bold mb-4" style={{ fontFamily: 'Fira Sans' }}>
          📦 Export Formats
        </h5>

        <div className="flex flex-wrap gap-3">
          {allFormats.map((fmt) => (
            <label key={fmt.id} className="flex items-center gap-2 cursor-pointer text-sm text-[#e0e0e0]">
              <input
                type="checkbox"
                className="w-4 h-4 rounded border border-white/[0.06] bg-white/[0.03] accent-[#c8956c]"
                checked={exportFormats.includes(fmt.id)}
                onChange={() => toggleFormat(fmt.id)}
              />
              {fmt.emoji} {fmt.label}
            </label>
          ))}
        </div>
      </div>

      {/* ─── Actions ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <button
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm text-[#999] hover:bg-white/[0.06] transition-colors duration-150 disabled:opacity-50"
          onClick={onRegenerate}
          disabled={isLoading}
        >
          {isLoading ? (
            <div className="w-4 h-4 border-2 border-[#999] border-t-transparent rounded-full animate-spin" />
          ) : (
            <RefreshCw size={16} />
          )}
          Regenerate Plan
        </button>

        <button
          className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-br from-[#6366f1] to-[#8b5cf6] text-white text-base font-medium transition-opacity hover:opacity-90 disabled:opacity-50"
          onClick={() => onApprove(steps, subQueries, exportFormats)}
          disabled={isLoading || steps.length === 0}
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Play size={20} />
          )}
          Approve & Start Research
        </button>
      </div>
    </div>
  );
}
