import { useState } from 'react';
import { FileText, Table, Brain, Download } from 'lucide-react';
import { api } from '../../api/client';

type Props = {
  runId: string;
};

type ExportFormat = {
  id: string;
  label: string;
  description: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  color: string;
  extension: string;
};

const FORMATS: ExportFormat[] = [
  {
    id: 'markdown',
    label: 'Markdown',
    description: 'Clean, portable research report',
    icon: FileText,
    color: '#999',
    extension: '.md',
  },
  {
    id: 'pdf',
    label: 'PDF Document',
    description: 'Print-ready styled report',
    icon: FileText,
    color: '#c45a5a',
    extension: '.pdf',
  },
  {
    id: 'docx',
    label: 'Word Document',
    description: 'Editable document with formatting',
    icon: FileText,
    color: '#3b82f6',
    extension: '.docx',
  },
  {
    id: 'xlsx',
    label: 'Excel Spreadsheet',
    description: 'Citations + research steps data',
    icon: Table,
    color: '#7dac5a',
    extension: '.xlsx',
  },
  {
    id: 'mindmap_json',
    label: 'Mindmap JSON',
    description: 'G6-compatible graph for re-import',
    icon: Brain,
    color: '#8b5cf6',
    extension: '.json',
  },
];

export function ExportPanel({ runId }: Props) {
  const [loadingFormats, setLoadingFormats] = useState<Set<string>>(new Set());
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleDownload = async (format: ExportFormat) => {
    setLoadingFormats((prev) => new Set(prev).add(format.id));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[format.id];
      return next;
    });

    try {
      const blob = await api.exportRun(runId, format.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `research_${runId}${format.extension}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setErrors((prev) => ({
        ...prev,
        [format.id]: err instanceof Error ? err.message : 'Download failed',
      }));
    } finally {
      setLoadingFormats((prev) => {
        const next = new Set(prev);
        next.delete(format.id);
        return next;
      });
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h4 className="text-xl font-bold" style={{ fontFamily: 'Fira Sans' }}>Export Research</h4>
        <p className="text-sm text-[#999] mt-1">
          Download your research in different formats for sharing and archival.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        {FORMATS.map((fmt) => {
          const isLoading = loadingFormats.has(fmt.id);
          const error = errors[fmt.id];

          return (
            <div
              key={fmt.id}
              className="p-6 rounded-xl border border-white/[0.06] bg-white/[0.03] cursor-pointer transition-all duration-150"
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = `${fmt.color}40`;
                e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '';
                e.currentTarget.style.transform = '';
              }}
            >
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `${fmt.color}18` }}
                  >
                    <span style={{ color: fmt.color }}><fmt.icon size={20} /></span>
                  </div>
                  <span className="px-2 py-0.5 text-[10px] rounded-full bg-[#555]/15 text-[#999]">
                    {fmt.extension}
                  </span>
                </div>

                <div>
                  <p className="font-semibold text-sm text-[#e0e0e0]">{fmt.label}</p>
                  <p className="text-xs text-[#999]">{fmt.description}</p>
                </div>

                {error && (
                  <p className="text-xs text-[#c45a5a]">{error}</p>
                )}

                <button
                  className="flex items-center justify-center gap-2 w-full px-3 py-2 rounded-xl text-sm transition-colors duration-150 disabled:opacity-50"
                  style={{ backgroundColor: `${fmt.color}18`, color: fmt.color }}
                  onClick={() => handleDownload(fmt)}
                  disabled={isLoading}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = `${fmt.color}28`;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = `${fmt.color}18`;
                  }}
                >
                  {isLoading ? (
                    <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Download size={14} />
                  )}
                  Download
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
