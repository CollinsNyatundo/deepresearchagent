import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router';
import { FileText, Table, Download, BookCopy } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api } from '../../api/client';
import type { ResearchResult } from '../../types/api';

type Props = {
  runId: string;
};

/** Download helper — triggers browser download from a Blob */
async function downloadExport(runId: string, format: string, filename: string) {
  const blob = await api.exportRun(runId, format);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const EXPORT_BUTTONS: {
  format: string;
  label: string;
  icon: React.ReactNode;
  ext: string;
  color: string;
}[] = [
  { format: 'pdf',      label: 'PDF',      icon: <FileText size={14} />,      ext: '.pdf',  color: '#c45a5a'    },
  { format: 'docx',     label: 'Word',     icon: <FileText size={14} />,     ext: '.docx', color: '#3b82f6'   },
  { format: 'xlsx',     label: 'Excel',    icon: <Table size={14} />,  ext: '.xlsx', color: '#7dac5a'  },
  { format: 'markdown', label: 'Markdown', icon: <FileText size={14} />,         ext: '.md',   color: '#999'   },
];

export function ReportView({ runId }: Props) {
  const navigate = useNavigate();
  const [markdown, setMarkdown] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [runDetails, setRunDetails] = useState<ResearchResult | null>(null);
  const [disabledDomains, setDisabledDomains] = useState<string[]>([]);
  const [resynthesizing, setResynthesizing] = useState(false);
  const [highlightedCitationId, setHighlightedCitationId] = useState<string | null>(null);
  const [hoveredCitationId, setHoveredCitationId] = useState<string | null>(null);
  const [savingToNotes, setSavingToNotes] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setDisabledDomains([]);
    api
      .getReport(runId)
      .then(setMarkdown)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));

    api
      .getRunDetails(runId)
      .then(setRunDetails)
      .catch((err) => console.error('Failed to fetch run details:', err));

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [runId]);

  useEffect(() => {
    const handleReportHighlight = (e: Event) => {
      const customEvent = e as CustomEvent<{ id: string }>;
      const { id } = customEvent.detail;
      if (id) {
        const normalizedId = id.startsWith('c') ? id : `c${id}`;
        setHighlightedCitationId(normalizedId);
      }
    };

    const handleReportClearHighlight = () => {
      setHighlightedCitationId(null);
    };

    window.addEventListener('highlight-citation-in-report', handleReportHighlight);
    window.addEventListener('clear-highlight-citation-in-report', handleReportClearHighlight);

    return () => {
      window.removeEventListener('highlight-citation-in-report', handleReportHighlight);
      window.removeEventListener('clear-highlight-citation-in-report', handleReportClearHighlight);
    };
  }, []);

  const handleToggleDomain = (domain: string) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    const nextDisabled = disabledDomains.includes(domain)
      ? disabledDomains.filter((d) => d !== domain)
      : [...disabledDomains, domain];
    
    setDisabledDomains(nextDisabled);
    setResynthesizing(true);
    setMarkdown('');
    
    const controller = api.resynthesizeRun(
      runId,
      nextDisabled,
      (event) => {
        if (event.event === 'report_chunk') {
          setMarkdown((prev) => prev + (event.data.chunk || ''));
        } else if (event.event === 'generating_report') {
          setMarkdown('');
        }
      },
      () => {
        setResynthesizing(false);
        api.getRunDetails(runId).then((details) => {
          setRunDetails(details);
          setMarkdown(details.report);
          
          const event = new CustomEvent('resynthesis-complete', { detail: { runId } });
          window.dispatchEvent(event);
        });
      },
      (err) => {
        console.error('Resynthesis failed:', err);
        setResynthesizing(false);
      }
    );
    
    abortControllerRef.current = controller;
  };

  const handleDownload = async (format: string, ext: string) => {
    setDownloading(format);
    try {
      await downloadExport(runId, format, `research_${runId}${ext}`);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setDownloading(null);
    }
  };

  const handleSaveToNotes = async () => {
    if (!runDetails) return
    setSavingToNotes(true)
    setSaveMessage(null)
    try {
      const workspaceId = runDetails.workspace_id || ''
      const noteTitle = `Research: ${runDetails.query || 'Untitled'}`
      const noteContent = `${markdown}\n\n---\n\n*Research run: [[run:${runId}]]*`
      const note = await api.createNote({
        workspace_id: workspaceId,
        title: noteTitle,
        content: noteContent,
        tags: ['research'],
        source: '',
      })
      setSaveMessage(`Saved to note: "${note.title}"`)
      setTimeout(() => setSaveMessage(null), 3000)
    } catch (err) {
      setSaveMessage(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSavingToNotes(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-2 border-[#c8956c] border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-[#999]">Loading report…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-24">
        <span className="text-sm text-[#c45a5a]">{error}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Download header bar */}
      <div className="flex items-center justify-between gap-4 px-8 pt-4">
        <div className="flex items-center gap-2 flex-wrap flex-1">
          {runDetails?.citations && runDetails.citations.length > 0 && (
            <>
              <span className="text-xs font-semibold text-[#999]">Exclude Sources:</span>
              {Array.from(new Set(runDetails.citations.map((c) => c.domain).filter((d): d is string => !!d))).map((domain) => {
                const isDisabled = disabledDomains.includes(domain);
                return (
                  <span
                    key={domain}
                    className="inline-flex items-center px-2.5 py-1 rounded-full text-xs cursor-pointer font-mono transition-colors duration-150"
                    style={{
                      backgroundColor: isDisabled ? 'transparent' : '#c8956c',
                      color: isDisabled ? '#999' : '#000',
                      border: isDisabled ? '1px solid #555' : 'none',
                      textDecoration: isDisabled ? 'line-through' : 'none',
                    }}
                    onClick={() => handleToggleDomain(domain)}
                  >
                    {domain} {isDisabled ? '+' : '×'}
                  </span>
                );
              })}
            </>
          )}
        </div>
        
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs text-[#999] mr-2">
            <Download size={12} className="inline align-middle mr-1" />
            Download as:
          </span>
          {EXPORT_BUTTONS.map(({ format, label, icon, ext, color }) => (
            <button
              key={format}
              title={`Download ${label}`}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs transition-colors duration-150 disabled:opacity-50"
              style={{ backgroundColor: `${color}18`, color }}
              onClick={() => handleDownload(format, ext)}
              disabled={downloading === format}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = `${color}28`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = `${color}18`;
              }}
            >
              {downloading === format ? (
                <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
              ) : (
                icon
              )}
              {label}
            </button>
          ))}
          <div className="w-px h-4 bg-white/[0.1] mx-1" />
          <button
            onClick={handleSaveToNotes}
            disabled={savingToNotes}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs transition-colors duration-150 disabled:opacity-50"
            style={{ backgroundColor: '#c8956c18', color: '#c8956c' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#c8956c28';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#c8956c18';
            }}
          >
            {savingToNotes ? (
              <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              <BookCopy size={14} />
            )}
            Save to Notes
          </button>
        </div>
      </div>

      {saveMessage && (
        <div className="flex items-center justify-center py-1">
          <span className="text-xs text-[#7dac5a]">{saveMessage}</span>
        </div>
      )}

      {/* Resynthesizing overlay loader */}
      {resynthesizing && (
        <div className="flex items-center justify-center py-2">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-[#c8956c] border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-[#c8956c]">Filtering sources and regenerating report...</span>
          </div>
        </div>
      )}

      {/* Report content */}
      <div
        className="p-8 rounded-xl border border-white/[0.06] bg-white/[0.03]"
        style={{
          maxWidth: 900,
          margin: '0 auto',
          width: '100%',
          color: '#e0e0e0',
        }}
      >
        <div className="report-content">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ href, children }) => {
                const urlStr = href || '';

                // Handle wiki-style links (wiki:, note:, doc:, run:)
                if (urlStr.startsWith('wiki:') || urlStr.startsWith('note:') || urlStr.startsWith('doc:') || urlStr.startsWith('run:')) {
                  const parts = urlStr.split(':');
                  const type = parts[0];
                  const target = parts.slice(1).join(':');
                  const handleClick = (e: React.MouseEvent) => {
                    e.preventDefault();
                    if (type === 'note') navigate(`/notes?note=${encodeURIComponent(target)}`);
                    else if (type === 'run') navigate(`/research?run=${target}`);
                    else if (type === 'doc') navigate(`/documents?doc=${target}`);
                    else if (type === 'wiki') navigate(`/documents?wiki=${encodeURIComponent(target)}`);
                  };
                  return (
                    <span onClick={handleClick} className="wiki-link cursor-pointer">
                      {children}
                    </span>
                  );
                }

                const linkText = String(children);
                const citationMatch = linkText.match(/\[(\d+)\]?/);
                const citationNum = citationMatch ? parseInt(citationMatch[1], 10) : null;

                let citation = runDetails?.citations?.find(c => {
                  if (c.url === urlStr) return true;
                  const normUrl = (url: string) => {
                    if (!url) return '';
                    return url.replace(/https?:\/\/(www\.)?/, '').replace(/\/$/, '').toLowerCase();
                  };
                  try {
                    if (urlStr && normUrl(c.url) === normUrl(urlStr)) return true;
                  } catch {}
                  if (citationNum !== null && (c.id === `c${citationNum}` || c.id === `${citationNum}`)) {
                    return true;
                  }
                  if (urlStr === `#${c.id}` || urlStr === `#c${c.id}`) {
                    return true;
                  }
                  return false;
                });

                if (!citation && citationNum !== null && runDetails?.citations) {
                  citation = runDetails.citations.find(c => c.id === `c${citationNum}` || c.id === `${citationNum}`);
                  if (!citation && citationNum <= runDetails.citations.length) {
                    citation = runDetails.citations[citationNum - 1];
                  }
                }

                if (citation) {
                  const citeId = citation.id.startsWith('c') ? citation.id : `c${citation.id}`;
                  const isItemHighlighted = highlightedCitationId === citeId;

                  return (
                    <span
                      className="relative inline-block"
                      onMouseEnter={() => {
                        setHoveredCitationId(citeId);
                        const event = new CustomEvent('highlight-citation', {
                          detail: { url: citation?.url, id: citation?.id }
                        });
                        window.dispatchEvent(event);
                      }}
                      onMouseLeave={() => {
                        setHoveredCitationId(null);
                        const event = new CustomEvent('clear-highlight-citation');
                        window.dispatchEvent(event);
                      }}
                    >
                      <a
                        href={citation.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="transition-all duration-200"
                        style={{
                          fontWeight: isItemHighlighted ? 700 : 500,
                          color: isItemHighlighted ? '#c8956c' : '#7dac5a',
                          textShadow: isItemHighlighted ? '0 0 8px #c8956c' : 'none',
                          backgroundColor: isItemHighlighted ? 'rgba(200, 149, 108, 0.15)' : 'transparent',
                          padding: isItemHighlighted ? '1px 4px' : '0',
                          borderRadius: '3px',
                        }}
                      >
                        {children}
                      </a>
                      {hoveredCitationId === citeId && (
                        <div className="absolute z-50 left-1/2 -translate-x-1/2 bottom-full mb-2 w-[280px] p-4 rounded-xl bg-[#0a0a0a] border border-[#333] shadow-xl">
                          <div className="flex flex-col gap-1.5">
                            <span className="text-xs font-bold line-clamp-2" style={{ lineHeight: '1.2', color: '#e0e0e0' }}>
                              {citation.title || 'Source Article'}
                            </span>
                            {citation.domain && (
                              <span className="px-2 py-0.5 text-[10px] rounded-full bg-[#c8956c] text-[#000] w-fit font-mono">
                                {citation.domain}
                              </span>
                            )}
                            {citation.snippet && (
                              <span className="text-xs line-clamp-4 whitespace-pre-wrap text-[#999]">
                                "{citation.snippet}"
                              </span>
                            )}
                            <a href={citation.url} target="_blank" rel="noopener noreferrer" className="text-xs truncate text-[#7dac5a] hover:text-[#d4a574] transition-colors">
                              {citation.url}
                            </a>
                          </div>
                        </div>
                      )}
                    </span>
                  );
                }

                return (
                  <a href={urlStr} target="_blank" rel="noopener noreferrer" className="text-[#7dac5a] hover:text-[#d4a574] transition-colors duration-150">
                    {children}
                  </a>
                );
              },
              code: ({ node, className, children, ...props }) => {
                const match = /language-(\w+)/.exec(className || '');
                const isGenUI = match && match[1] === 'genui';
                const content = String(children).trim();
                const inline = !match;

                if (isGenUI) {
                  try {
                    const data = JSON.parse(content);
                    if (data.type === 'comparison_table') {
                      return (
                        <div className="p-4 my-4 rounded-xl bg-[#0a0a0a] border border-[#333]">
                          <p className="text-sm font-bold mb-2 text-[#c8956c]">{data.title || 'Comparison Table'}</p>
                          <table className="w-full text-[#e0e0e0]">
                            <thead>
                              <tr className="border-b border-[#333]">
                                {data.headers?.map((h: string, idx: number) => (
                                  <th key={idx} className="text-left py-2 px-3 text-xs text-[#999]">{h}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {data.rows?.map((row: any[], rowIdx: number) => (
                                <tr key={rowIdx} className="border-b border-[#333]">
                                  {row.map((cell: any, cellIdx: number) => (
                                    <td key={cellIdx} className="py-2 px-3 text-sm">{cell}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      );
                    }
                    if (data.type === 'timeline') {
                      return (
                        <div className="p-4 my-4 rounded-xl bg-[#0a0a0a] border border-[#333]">
                          <p className="text-sm font-bold mb-2 text-[#c8956c]">{data.title || 'Timeline'}</p>
                          <div className="relative">
                            <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-[#333]" />
                            {data.events?.map((ev: any, idx: number) => (
                              <div key={idx} className="relative flex gap-4 mb-4">
                                <div className="w-6 h-6 rounded-full bg-[#c8956c] flex items-center justify-center flex-shrink-0">
                                  <div className="w-2 h-2 rounded-full bg-[#000]" />
                                </div>
                                <div>
                                  <div className="text-sm font-medium text-[#e0e0e0]">{ev.title}</div>
                                  <div className="text-xs text-[#999]">{ev.date}</div>
                                  <div className="text-xs text-[#999] mt-1">{ev.description}</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    }
                    return (
                      <pre style={{ backgroundColor: '#0a0a0a', padding: 12, borderRadius: 4, overflowX: 'auto' }}>
                        <code>{content}</code>
                      </pre>
                    );
                  } catch (e) {
                    return (
                      <div className="p-4 my-4 rounded-xl bg-[#0a0a0a] border border-[#333]">
                        <p className="text-xs text-[#c8956c] mb-2">Streaming GenUI component...</p>
                        <div className="flex flex-col gap-2">
                          <div className="h-5 bg-[#333] rounded animate-pulse" />
                          <div className="h-5 bg-[#333] rounded animate-pulse w-[70%]" />
                          <div className="h-5 bg-[#333] rounded animate-pulse w-[50%]" />
                        </div>
                      </div>
                    );
                  }
                }

                return inline ? (
                  <code className={className} {...props}>
                    {children}
                  </code>
                ) : (
                  <pre style={{ backgroundColor: '#0a0a0a', padding: 12, borderRadius: 4, overflowX: 'auto', border: '1px solid #333' }}>
                    <code className={className} {...props}>
                      {children}
                    </code>
                  </pre>
                );
              }
            }}
          >
            {markdown.replace(/\[\[([^\]]+)\]\]/g, (_match: string, inner: string) => `[${inner}](${inner.includes(':') ? inner : 'wiki:' + inner})`)}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
