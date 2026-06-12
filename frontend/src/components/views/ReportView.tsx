import { useEffect, useState, useRef } from 'react';
import {
  Paper,
  Loader,
  Center,
  Text,
  Stack,
  Group,
  Button,
  Tooltip,
  HoverCard,
  Anchor,
  Badge,
  Table,
  Timeline,
  Skeleton,
} from '@mantine/core';
import {
  IconFileTypePdf,
  IconFileTypeDocx,
  IconFileSpreadsheet,
  IconMarkdown,
  IconDownload,
} from '@tabler/icons-react';
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
  { format: 'pdf',      label: 'PDF',      icon: <IconFileTypePdf size={14} />,      ext: '.pdf',  color: 'red'    },
  { format: 'docx',     label: 'Word',     icon: <IconFileTypeDocx size={14} />,     ext: '.docx', color: 'blue'   },
  { format: 'xlsx',     label: 'Excel',    icon: <IconFileSpreadsheet size={14} />,  ext: '.xlsx', color: 'green'  },
  { format: 'markdown', label: 'Markdown', icon: <IconMarkdown size={14} />,         ext: '.md',   color: 'gray'   },
];

export function ReportView({ runId }: Props) {
  const [markdown, setMarkdown] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [runDetails, setRunDetails] = useState<ResearchResult | null>(null);
  const [disabledDomains, setDisabledDomains] = useState<string[]>([]);
  const [resynthesizing, setResynthesizing] = useState(false);
  const [highlightedCitationId, setHighlightedCitationId] = useState<string | null>(null);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setDisabledDomains([]); // reset on run change
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
        // Refresh run details
        api.getRunDetails(runId).then((details) => {
          setRunDetails(details);
          setMarkdown(details.report);
          
          // Fire a custom event to notify graphs to reload data
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

  if (loading) {
    return (
      <Center py={100}>
        <Stack align="center" gap="xs">
          <Loader size="lg" />
          <Text size="sm" c="dimmed">Loading report…</Text>
        </Stack>
      </Center>
    );
  }

  if (error) {
    return (
      <Center py={100}>
        <Text c="red" size="sm">{error}</Text>
      </Center>
    );
  }

  return (
    <Stack gap="md">
      {/* Download header bar */}
      <Group justify="space-between" align="center" px="xl" pt="md">
        <Group gap="xs" style={{ flexWrap: 'wrap', flex: 1 }}>
          {runDetails?.citations && runDetails.citations.length > 0 && (
            <>
              <Text size="xs" fw={600} c="dimmed">Exclude Sources:</Text>
              {Array.from(new Set(runDetails.citations.map((c) => c.domain).filter((d): d is string => !!d))).map((domain) => {
                const isDisabled = disabledDomains.includes(domain);
                return (
                  <Badge
                    key={domain}
                    color={isDisabled ? "gray" : "mint"}
                    variant={isDisabled ? "outline" : "filled"}
                    style={{ cursor: 'pointer', textDecoration: isDisabled ? 'line-through' : 'none' }}
                    onClick={() => handleToggleDomain(domain)}
                  >
                    {domain} {isDisabled ? '+' : '×'}
                  </Badge>
                );
              })}
            </>
          )}
        </Group>
        
        <Group gap="xs">
          <Text size="xs" c="dimmed" mr={4}>
            <IconDownload size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />
            Download as:
          </Text>
          {EXPORT_BUTTONS.map(({ format, label, icon, ext, color }) => (
            <Tooltip key={format} label={`Download ${label}`} withArrow>
              <Button
                size="xs"
                variant="light"
                color={color}
                leftSection={icon}
                loading={downloading === format}
                onClick={() => handleDownload(format, ext)}
              >
                {label}
              </Button>
            </Tooltip>
          ))}
        </Group>
      </Group>

      {/* Resynthesizing overlay loader */}
      {resynthesizing && (
        <Center py="xs">
          <Group gap="xs">
            <Loader size="xs" />
            <Text size="xs" c="mint">Filtering sources and regenerating report...</Text>
          </Group>
        </Center>
      )}

      {/* Report content */}
      <Paper
        p="xl"
        shadow="xs"
        style={{
          maxWidth: 900,
          margin: '0 auto',
          width: '100%',
          backgroundColor: 'var(--color-slate-900)',
          border: '1px solid var(--color-slate-800)',
          color: 'var(--color-text-main)'
        }}
      >
        <div className="report-content">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ href, children }) => {
                const linkText = String(children);
                const citationMatch = linkText.match(/\[?(\d+)\]?/);
                const citationNum = citationMatch ? parseInt(citationMatch[1], 10) : null;
                const urlStr = href || '';

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
                    <HoverCard width={280} shadow="md" withArrow openDelay={200} closeDelay={100}>
                      <HoverCard.Target>
                        <Anchor
                          href={citation.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            fontWeight: isItemHighlighted ? 700 : 500,
                            color: isItemHighlighted ? 'var(--color-gold-500)' : 'var(--color-mint-500)',
                            textShadow: isItemHighlighted ? '0 0 8px var(--color-gold-500)' : 'none',
                            backgroundColor: isItemHighlighted ? 'rgba(245, 158, 11, 0.15)' : 'transparent',
                            padding: isItemHighlighted ? '1px 4px' : '0',
                            borderRadius: '3px',
                            transition: 'color 200ms ease, background-color 200ms ease, text-shadow 200ms ease',
                          }}
                          onMouseEnter={() => {
                            const event = new CustomEvent('highlight-citation', {
                              detail: { url: citation?.url, id: citation?.id }
                            });
                            window.dispatchEvent(event);
                          }}
                          onMouseLeave={() => {
                            const event = new CustomEvent('clear-highlight-citation');
                            window.dispatchEvent(event);
                          }}
                        >
                          {children}
                        </Anchor>
                      </HoverCard.Target>
                      <HoverCard.Dropdown style={{ backgroundColor: 'var(--color-slate-950)', borderColor: 'var(--color-slate-800)', color: 'var(--color-text-main)' }}>
                        <Stack gap={6}>
                          <Text size="xs" fw={700} lineClamp={2} style={{ lineHeight: '1.2', color: 'var(--color-text-main)' }}>
                            {citation.title || 'Source Article'}
                          </Text>
                          {citation.domain && (
                            <Badge size="xxs" color="mint" variant="filled" style={{ width: 'fit-content' }}>
                              {citation.domain}
                            </Badge>
                          )}
                          {citation.snippet && (
                            <Text size="xxs" lineClamp={4} style={{ whiteSpace: 'pre-wrap', color: 'var(--color-text-muted)' }}>
                              "{citation.snippet}"
                            </Text>
                          )}
                          <Anchor href={citation.url} target="_blank" rel="noopener noreferrer" size="xxs" truncate style={{ color: 'var(--color-mint-500)' }}>
                            {citation.url}
                          </Anchor>
                        </Stack>
                      </HoverCard.Dropdown>
                    </HoverCard>
                  );
                }

                return (
                  <Anchor href={urlStr} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-mint-500)' }}>
                    {children}
                  </Anchor>
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
                        <Paper p="md" my="md" style={{ backgroundColor: 'var(--color-slate-950)', border: '1px solid var(--color-slate-800)' }}>
                          <Text size="sm" fw={700} mb="xs" c="var(--color-mint-500)">{data.title || 'Comparison Table'}</Text>
                          <Table variant="simple" style={{ color: 'var(--color-text-main)' }}>
                            <Table.Thead>
                              <Table.Tr style={{ borderBottomColor: 'var(--color-slate-800)' }}>
                                {data.headers?.map((h: string, idx: number) => (
                                  <Table.Th key={idx} style={{ color: 'var(--color-text-muted)' }}>{h}</Table.Th>
                                ))}
                              </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                              {data.rows?.map((row: any[], rowIdx: number) => (
                                <Table.Tr key={rowIdx} style={{ borderBottomColor: 'var(--color-slate-800)' }}>
                                  {row.map((cell: any, cellIdx: number) => (
                                    <Table.Td key={cellIdx}>{cell}</Table.Td>
                                  ))}
                                </Table.Tr>
                              ))}
                            </Table.Tbody>
                          </Table>
                        </Paper>
                      );
                    }
                    if (data.type === 'timeline') {
                      return (
                        <Paper p="md" my="md" style={{ backgroundColor: 'var(--color-slate-950)', border: '1px solid var(--color-slate-800)' }}>
                          <Text size="sm" fw={700} mb="xs" c="var(--color-mint-500)">{data.title || 'Timeline'}</Text>
                          <Timeline active={(data.events?.length || 1) - 1} bulletSize={24} lineWidth={2} color="mint">
                            {data.events?.map((ev: any, idx: number) => (
                              <Timeline.Item key={idx} title={ev.title} style={{ color: 'var(--color-text-main)' }}>
                                <Text c="dimmed" size="xs">{ev.date}</Text>
                                <Text size="xs" mt={4} style={{ color: 'var(--color-text-muted)' }}>{ev.description}</Text>
                              </Timeline.Item>
                            ))}
                          </Timeline>
                        </Paper>
                      );
                    }
                    return (
                      <pre style={{ backgroundColor: 'var(--color-slate-950)', padding: 12, borderRadius: 4, overflowX: 'auto' }}>
                        <code>{content}</code>
                      </pre>
                    );
                  } catch (e) {
                    return (
                      <Paper p="md" my="md" style={{ backgroundColor: 'var(--color-slate-950)', border: '1px solid var(--color-slate-800)' }}>
                        <Text size="xs" c="var(--color-mint-500)" mb={8}>Streaming GenUI component...</Text>
                        <Stack gap={8}>
                          <Skeleton height={20} radius="xs" />
                          <Skeleton height={20} width="70%" radius="xs" />
                          <Skeleton height={20} width="50%" radius="xs" />
                        </Stack>
                      </Paper>
                    );
                  }
                }

                return inline ? (
                  <code className={className} {...props}>
                    {children}
                  </code>
                ) : (
                  <pre style={{ backgroundColor: 'var(--color-slate-950)', padding: 12, borderRadius: 4, overflowX: 'auto', border: '1px solid var(--color-slate-800)' }}>
                    <code className={className} {...props}>
                      {children}
                    </code>
                  </pre>
                );
              }
            }}
          >
            {markdown}
          </ReactMarkdown>
        </div>
      </Paper>
    </Stack>
  );
}
