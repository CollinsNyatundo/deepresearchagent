import { useState, useEffect, useRef } from 'react';
import {
  Stack,
  Paper,
  Text,
  Title,
  Group,
  Badge,
  Timeline,
  ThemeIcon,
  Progress,
  Loader,
  RingProgress,
  Alert,
  Code,
  Accordion,
  Divider,
  Anchor,
  Tooltip,
  Table,
} from '@mantine/core';
import {
  IconSearch,
  IconFileText,
  IconBrain,
  IconCheck,
  IconAlertTriangle,
  IconRefresh,
  IconFilter,
  IconWriting,
  IconListCheck,
  IconNetwork,
  IconBulb,
} from '@tabler/icons-react';
import type { ResearchEvent } from '../../types/api';

type Props = {
  events: ResearchEvent[];
  isActive: boolean;
};

interface ScrapedPageInfo {
  url: string;
  title?: string;
  success: boolean;
  fetcher_used?: string;
  content_length?: number;
  original_status?: number;
  fallback_attempts?: string[];
  error?: string;
}

interface SearchResultInfo {
  url: string;
  title?: string;
  snippet?: string;
  score: number;
  relevance_score?: number;
  eval_rationale?: string;
}

interface CycleData {
  cycle: number;
  query?: string;
  search_results?: SearchResultInfo[];
  scraped_pages?: ScrapedPageInfo[];
  answerLength?: number;
  citationCount?: number;
  planUpdated?: boolean;
  confidenceScore?: number;
  confidenceReasoning?: string;
  needsMoreResearch?: boolean;
  progressPercent?: number;
  isReflecting?: boolean;
  isSearching?: boolean;
  isScraping?: boolean;
  isValidating?: boolean;
  isSynthesizing?: boolean;
}

const STATE_CONFIG: Record<
  string,
  { icon: typeof IconSearch; color: string; label: string }
> = {
  initializing: { icon: IconNetwork, color: 'gray', label: 'Initializing' },
  classifying_intent: { icon: IconBulb, color: 'violet', label: 'Classifying Intent' },
  planning: { icon: IconListCheck, color: 'violet', label: 'Creating Plan' },
  plan_ready: { icon: IconCheck, color: 'green', label: 'Plan Ready' },
  decomposing: { icon: IconBrain, color: 'cyan', label: 'Decomposing Query' },
  searching: { icon: IconSearch, color: 'blue', label: 'Searching' },
  scraping: { icon: IconFileText, color: 'orange', label: 'Scraping Pages' },
  validating: { icon: IconFilter, color: 'teal', label: 'Validating Results' },
  synthesizing: { icon: IconBrain, color: 'indigo', label: 'Synthesizing' },
  reflecting: { icon: IconBrain, color: 'grape', label: 'Reflecting' },
  retrying: { icon: IconRefresh, color: 'yellow', label: 'Retrying' },
  cycle_complete: { icon: IconCheck, color: 'green', label: 'Cycle Complete' },
  generating_report: {
    icon: IconWriting,
    color: 'pink',
    label: 'Writing Report',
  },
  complete: { icon: IconCheck, color: 'green', label: 'Complete' },
  error: { icon: IconAlertTriangle, color: 'red', label: 'Error' },
};

export function ResearchProgress({ events, isActive }: Props) {
  const [currentCycle, setCurrentCycle] = useState(0);
  const [maxCycles, setMaxCycles] = useState(0);
  const [progressPercent, setProgressPercent] = useState(0);
  const [currentState, setCurrentState] = useState('initializing');
  const [cycles, setCycles] = useState<CycleData[]>([]);
  const [intentData, setIntentData] = useState<any>(null);
  const [thinkingText, setThinkingText] = useState('');
  const [scrapeProgress, setScrapeProgress] = useState<Record<string, any>>({});
  const timelineEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const cycleMap: Record<number, CycleData> = {};
    let foundIntent = null;
    let thinking = '';
    const nextScrapeProgress: Record<string, any> = {};

    for (const ev of events) {
      if (ev.data?.max_cycles) setMaxCycles(ev.data.max_cycles);
      if (ev.data?.progress) setProgressPercent(ev.data.progress);
      setCurrentState(ev.event);

      if (ev.event === 'plan_ready' && ev.data?.intent) {
        foundIntent = ev.data.intent;
      }

      if (ev.event === 'thinking_chunk' && ev.data?.chunk) {
        thinking += ev.data.chunk;
      }

      if (ev.event === 'scrape_progress' && ev.data) {
        const { url, status, details, cycle } = ev.data;
        const existing = nextScrapeProgress[url] || { url, status, cycle };
        existing.status = status;
        if (details?.fetcher) existing.fetcher = details.fetcher;
        if (details?.content_length) existing.contentLength = details.content_length;
        if (details?.error) existing.error = details.error;
        nextScrapeProgress[url] = existing;
      }

      if (ev.data?.cycle) {
        const cNum = ev.data.cycle;
        setCurrentCycle(cNum);
        if (!cycleMap[cNum]) {
          cycleMap[cNum] = {
            cycle: cNum,
            search_results: [],
            scraped_pages: [],
          };
        }
        const c = cycleMap[cNum];

        if (ev.event === 'searching') {
          c.query = ev.data.query;
          c.isSearching = true;
          c.isScraping = false;
          c.isValidating = false;
          c.isSynthesizing = false;
          c.isReflecting = false;
        } else if (ev.event === 'scraping') {
          c.isSearching = false;
          c.isScraping = true;
          if (ev.data.pages) {
            c.scraped_pages = ev.data.pages;
          }
          if (ev.data.search_results) {
            c.search_results = ev.data.search_results;
          }
        } else if (ev.event === 'validating') {
          c.isScraping = false;
          c.isValidating = true;
        } else if (ev.event === 'synthesizing') {
          c.isValidating = false;
          c.isSynthesizing = true;
        } else if (ev.event === 'reflecting') {
          c.isSynthesizing = false;
          c.isReflecting = true;
        } else if (ev.event === 'cycle_complete') {
          c.isReflecting = false;
          c.answerLength = ev.data.answer_length;
          c.citationCount = ev.data.citation_count;
          c.planUpdated = ev.data.plan_updated;
        } else if (ev.event === 'confidence') {
          c.confidenceScore = ev.data.score;
          c.confidenceReasoning = ev.data.reasoning;
          c.needsMoreResearch = ev.data.needs_more_research;
        } else if (ev.event === 'progress') {
          c.progressPercent = ev.data.progress;
        }
      }
    }

    const sortedCycles = Object.values(cycleMap).sort((a, b) => a.cycle - b.cycle);
    setCycles(sortedCycles);
    if (foundIntent) {
      setIntentData(foundIntent);
    }
    setThinkingText(thinking);
    setScrapeProgress(nextScrapeProgress);
  }, [events]);

  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  const stateConfig = STATE_CONFIG[currentState] || STATE_CONFIG.initializing;

  // Filter non-cycle events for the top/bottom static timeline items
  const nonCycleEvents = events.filter((ev) =>
    ['planning', 'plan_ready', 'decomposing', 'generating_report', 'complete', 'error'].includes(ev.event)
  );

  return (
    <Stack gap="lg">
      {/* ─── Status Header ─────────────────────────────────── */}
      <Paper p="lg" radius="md" withBorder style={{ backgroundColor: 'var(--color-slate-900)', borderColor: 'var(--color-slate-800)' }}>
        <Group justify="space-between" align="center">
          <Group>
            {isActive ? (
              <Loader size="sm" color={stateConfig.color} />
            ) : (
              <ThemeIcon
                size="lg"
                radius="xl"
                color={stateConfig.color}
                variant="light"
              >
                <stateConfig.icon size={20} />
              </ThemeIcon>
            )}
            <div>
              <Text fw={600} size="lg" style={{ fontFamily: 'Fira Sans' }}>
                {stateConfig.label}
              </Text>
              <Text size="sm" c="dimmed">
                {isActive ? 'Research in progress...' : 'Research completed'}
              </Text>
            </div>
          </Group>

          {maxCycles > 0 && (
            <RingProgress
              size={80}
              thickness={6}
              roundCaps
              sections={[
                {
                  value: maxCycles ? (currentCycle / maxCycles) * 100 : 0,
                  color: 'mint',
                },
              ]}
              label={
                <Text ta="center" size="xs" fw={700} style={{ fontFamily: 'Fira Code' }}>
                  {currentCycle}/{maxCycles}
                </Text>
              }
            />
          )}
        </Group>

        {maxCycles > 0 && (
          <Progress
            value={maxCycles ? (currentCycle / maxCycles) * 100 : 0}
            color="mint"
            size="sm"
            radius="xl"
            mt="md"
            animated={isActive}
          />
        )}

        {progressPercent > 0 && (
          <Group mt="xs" justify="space-between">
            <Text size="xs" c="dimmed">
              Research coverage
            </Text>
            <Badge
              size="sm"
              color={
                progressPercent >= 80
                  ? 'green'
                  : progressPercent >= 50
                  ? 'yellow'
                  : 'orange'
              }
            >
              {progressPercent}%
            </Badge>
          </Group>
        )}
      </Paper>

      {/* ─── Intent classification Details (If Available) ─── */}
      {intentData && (
        <Paper p="lg" radius="md" withBorder style={{ backgroundColor: 'var(--color-slate-900)', borderColor: 'var(--color-slate-800)' }}>
          <Group mb="xs">
            <ThemeIcon color="violet" size="md" radius="xl">
              <IconBulb size={16} />
            </ThemeIcon>
            <Title order={5}>Query Intent Classified</Title>
            <Badge
              color={
                intentData.category === 'academic'
                  ? 'purple'
                  : intentData.category === 'news'
                  ? 'teal'
                  : intentData.category === 'technical'
                  ? 'blue'
                  : 'gray'
              }
            >
              {intentData.category.toUpperCase()}
            </Badge>
          </Group>
          <Text size="sm" c="dimmed" mb="md">
            {intentData.rationale}
          </Text>
          <Group gap="lg">
            {intentData.target_domains?.length > 0 && (
              <div>
                <Text size="xs" fw={600} mb={4} c="dimmed">
                  🎯 Target Domains:
                </Text>
                <Group gap={4}>
                  {intentData.target_domains.map((d: string) => (
                    <Badge key={d} size="xs" color="green" variant="outline">
                      {d}
                    </Badge>
                  ))}
                </Group>
              </div>
            )}
            {intentData.avoid_domains?.length > 0 && (
              <div>
                <Text size="xs" fw={600} mb={4} c="dimmed">
                  🚫 Avoid Domains:
                </Text>
                <Group gap={4}>
                  {intentData.avoid_domains.map((d: string) => (
                    <Badge key={d} size="xs" color="red" variant="outline">
                      {d}
                    </Badge>
                  ))}
                </Group>
              </div>
            )}
          </Group>
        </Paper>
      )}

      {/* ─── Thinking Process ────────────────────────────────── */}
      {thinkingText && (
        <Paper p="lg" radius="md" withBorder style={{ backgroundColor: 'var(--color-slate-900)', borderColor: 'var(--color-slate-800)' }}>
          <Accordion defaultValue="thinking" styles={{
            item: { border: 'none' },
            control: {
              backgroundColor: 'transparent',
              padding: '0 12px 12px 12px',
              '&:hover': { backgroundColor: 'transparent' }
            },
            content: { padding: 0 }
          }}>
            <Accordion.Item value="thinking">
              <Accordion.Control icon={<IconBrain size={18} color="var(--color-mint-500)" />}>
                <Group justify="space-between">
                  <Text fw={600} size="sm" style={{ fontFamily: 'Fira Sans', color: 'var(--color-text-main)' }}>Thinking Process</Text>
                  {isActive && currentState !== 'complete' && <Loader size="xs" color="mint" />}
                </Group>
              </Accordion.Control>
              <Accordion.Panel>
                <div style={{
                  border: '1px solid var(--color-slate-800)',
                  borderRadius: '6px',
                  overflow: 'hidden'
                }}>
                  {/* Terminal Header */}
                  <div style={{
                    backgroundColor: 'var(--color-slate-950)',
                    padding: '8px 12px',
                    borderBottom: '1px solid var(--color-slate-800)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#ef4444', display: 'inline-block' }}></span>
                      <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#f59e0b', display: 'inline-block' }}></span>
                      <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#10b981', display: 'inline-block' }}></span>
                    </div>
                    <span style={{ fontSize: '0.75rem', fontFamily: 'Fira Code', color: 'var(--color-text-muted)' }}>
                      research_agent --verbose
                    </span>
                    <span style={{ width: '30px' }}></span>
                  </div>

                  <Code
                    block
                    className={isActive && currentState !== 'complete' ? 'blink-cursor' : ''}
                    style={{
                      maxHeight: '300px',
                      overflowY: 'auto',
                      whiteSpace: 'pre-wrap',
                      backgroundColor: '#000000',
                      color: 'var(--color-gold-500)',
                      fontFamily: 'Fira Code, monospace',
                      fontSize: '0.85rem',
                      padding: '16px',
                      border: 'none',
                      borderRadius: 0,
                    }}
                  >
                    {thinkingText}
                  </Code>
                </div>
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>
        </Paper>
      )}

      {/* ─── Scraper Queue Dashboard ─────────────────────────── */}
      {Object.keys(scrapeProgress).length > 0 && (
        <Paper p="lg" radius="md" withBorder style={{ backgroundColor: 'var(--color-slate-900)', borderColor: 'var(--color-slate-800)' }}>
          <Title order={5} mb="xs" style={{ fontFamily: 'Fira Sans', fontWeight: 600 }}>Scraper Queue Dashboard</Title>
          <Text size="xs" c="dimmed" mb="md">Real-time status of pages being fetched and analyzed</Text>
          <div style={{ overflowX: 'auto' }}>
            <Table className="telemetry-table" verticalSpacing="xs">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th style={{ width: '60px' }}>Cycle</Table.Th>
                  <Table.Th>Domain</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Fetcher</Table.Th>
                  <Table.Th style={{ width: '90px' }}>Size</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {Object.values(scrapeProgress).map((p, idx) => {
                  let domain = p.url;
                  try {
                    domain = new URL(p.url).hostname;
                  } catch {
                    // ignore
                  }
                  const isActiveRow = p.status === 'TRYING_TIER' || p.status === 'START';
                  let statusColor = 'gray';
                  if (p.status === 'COMPLETE' || p.status === 'CACHE_HIT') statusColor = 'mint';
                  else if (p.status === 'FAILED' || p.status === 'SKIPPED_CIRCUIT') statusColor = 'red';
                  else if (p.status === 'TRYING_TIER' || p.status === 'START') statusColor = 'yellow';

                  return (
                    <Table.Tr key={idx} className={isActiveRow ? 'active-row' : ''}>
                      <Table.Td ta="center">
                        <Badge size="xs" color="gray" variant="light" style={{ fontFamily: 'Fira Code' }}>{p.cycle}</Badge>
                      </Table.Td>
                      <Table.Td>
                        <Anchor href={p.url} target="_blank" size="xs" truncate style={{ maxWidth: '250px', display: 'inline-block', color: 'var(--color-text-main)' }}>
                          {domain}
                        </Anchor>
                      </Table.Td>
                      <Table.Td>
                        <Badge size="xs" color={statusColor} variant="filled" style={{ fontFamily: 'Fira Code' }}>{p.status}</Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" style={{ fontFamily: 'Fira Code' }}>{p.fetcher || '-'}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" style={{ fontFamily: 'Fira Code' }}>
                          {p.contentLength !== undefined ? `${(p.contentLength / 1024).toFixed(1)} KB` : '-'}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </div>
        </Paper>
      )}

      {/* ─── Event Timeline ────────────────────────────────── */}
      <Paper p="lg" radius="md" withBorder style={{ backgroundColor: 'var(--color-slate-900)', borderColor: 'var(--color-slate-800)' }}>
        <Title order={5} mb="md" style={{ fontFamily: 'Fira Sans', fontWeight: 600 }}>
          Research Timeline
        </Title>

        <Timeline bulletSize={28} lineWidth={2} active={cycles.length + nonCycleEvents.length - 1} color="mint">
          {/* Static Pre-run Steps */}
          {nonCycleEvents
            .filter((ev) => ['planning', 'plan_ready', 'decomposing'].includes(ev.event))
            .map((ev, idx) => {
              const cfg = STATE_CONFIG[ev.event] || STATE_CONFIG.initializing;
              return (
                <Timeline.Item
                  key={`pre-${idx}`}
                  bullet={
                    <ThemeIcon size={28} radius="xl" color={cfg.color} variant="filled">
                      <cfg.icon size={14} />
                    </ThemeIcon>
                  }
                  title={<Text size="sm" fw={500}>{cfg.label}</Text>}
                >
                  {ev.event === 'plan_ready' && (
                    <Stack gap={4} mt={4}>
                      {Array.isArray(ev.data.sub_queries) && ev.data.sub_queries.length > 0 && (
                        <>
                          <Text size="xs" c="dimmed">Sub-queries:</Text>
                          <Group gap={4} wrap="wrap">
                            {(ev.data.sub_queries as string[]).map((q, i) => (
                              <Badge key={i} size="xs" variant="dot" color="cyan">
                                {q.length > 50 ? q.slice(0, 50) + '…' : q}
                              </Badge>
                            ))}
                          </Group>
                        </>
                      )}
                      <Text size="xs" c="dimmed">
                        📋 {ev.data.step_count ?? 0} research steps planned
                      </Text>
                    </Stack>
                  )}
                </Timeline.Item>
              );
            })}

          {/* Dynamic Cycle-Grouped Steps */}
          {cycles.map((c) => {
            const isFinished = c.answerLength !== undefined;
            const CycleIcon = isFinished ? IconCheck : IconSearch;
            const color = isFinished ? 'mint' : 'blue';

            return (
              <Timeline.Item
                key={`cycle-${c.cycle}`}
                bullet={
                  <ThemeIcon size={28} radius="xl" color={color} variant={isFinished ? 'filled' : 'light'}>
                    {c.isScraping ? <IconFileText size={14} /> : <CycleIcon size={14} />}
                  </ThemeIcon>
                }
                title={
                  <Group gap="xs">
                    <Text size="sm" fw={600} style={{ fontFamily: 'Fira Sans' }}>
                      Cycle {c.cycle}
                    </Text>
                    {c.isSearching && <Badge size="xs" color="blue" variant="light">Searching</Badge>}
                    {c.isScraping && <Badge size="xs" color="orange" variant="light">Scraping</Badge>}
                    {c.isValidating && <Badge size="xs" color="teal" variant="light">Filtering</Badge>}
                    {c.isSynthesizing && <Badge size="xs" color="indigo" variant="light">Synthesizing</Badge>}
                    {c.isReflecting && <Badge size="xs" color="grape" variant="light">Reflecting</Badge>}
                    {isFinished && <Badge size="xs" color="mint" variant="filled">Complete</Badge>}
                  </Group>
                }
              >
                <Accordion variant="separated" mt="xs" styles={{
                  item: { backgroundColor: 'var(--color-slate-950)', borderColor: 'var(--color-slate-800)' },
                  control: { backgroundColor: 'transparent' },
                }}>
                  <Accordion.Item value="details">
                    <Accordion.Control>
                      <Text size="xs" fw={500} c="dimmed" style={{ fontFamily: 'Fira Sans' }}>
                        {c.query ? `Query: "${c.query.slice(0, 60)}..."` : 'Details & Scraped Contents'}
                      </Text>
                    </Accordion.Control>
                    <Accordion.Panel>
                      <Stack gap="sm">
                        {c.query && (
                          <div>
                            <Text size="xs" fw={600} c="dimmed" mb={2} style={{ fontFamily: 'Fira Sans' }}>🔍 Search Query:</Text>
                            <Code block style={{ backgroundColor: 'var(--color-slate-950)', border: '1px solid var(--color-slate-800)', color: 'var(--color-gold-500)', fontFamily: 'Fira Code' }}>{c.query}</Code>
                          </div>
                        )}

                        {/* Pointwise AutoEval Search relevance List */}
                        {c.search_results && c.search_results.length > 0 && (
                          <div>
                            <Text size="xs" fw={600} c="dimmed" mb={4} style={{ fontFamily: 'Fira Sans' }}>🎯 snippet AutoEval Relevance Scores:</Text>
                            <Stack gap={6}>
                              {c.search_results.map((r, i) => {
                                const score = r.relevance_score ?? 1.0;
                                const passed = score >= 0.7;
                                return (
                                  <Paper key={i} p="xs" withBorder radius="xs" style={{ background: 'var(--color-slate-900)', borderColor: 'var(--color-slate-800)' }}>
                                    <Group justify="space-between" align="flex-start" wrap="nowrap">
                                      <Stack gap={2} style={{ flex: 1 }}>
                                        <Anchor href={r.url} target="_blank" size="xs" fw={500} truncate style={{ color: 'var(--color-mint-500)' }}>
                                          {r.title || r.url}
                                        </Anchor>
                                        <Text size="xxs" c="dimmed" lineClamp={2} style={{ color: 'var(--color-text-muted)' }}>
                                          {r.snippet}
                                        </Text>
                                        {r.eval_rationale && (
                                          <Text size="xxs" style={{ fontStyle: 'italic', color: 'var(--color-text-muted)' }}>
                                            Judge: {r.eval_rationale}
                                          </Text>
                                        )}
                                      </Stack>
                                      <Badge size="xs" color={passed ? 'mint' : 'red'} variant="filled" style={{ fontFamily: 'Fira Code' }}>
                                        {score.toFixed(2)}
                                      </Badge>
                                    </Group>
                                  </Paper>
                                );
                              })}
                            </Stack>
                          </div>
                        )}

                        {/* Inline list of scraped pages with fallback diagnostics */}
                        {c.scraped_pages && c.scraped_pages.length > 0 && (
                          <div>
                            <Text size="xs" fw={600} c="dimmed" mb={4} style={{ fontFamily: 'Fira Sans' }}>📄 Scraped Content Fallbacks & Status:</Text>
                            <Stack gap={4}>
                              {c.scraped_pages.map((p, i) => {
                                const fetcherColor =
                                  p.fetcher_used === 'async_fetcher'
                                    ? 'green'
                                    : p.fetcher_used === 'dynamic_fetcher'
                                    ? 'orange'
                                    : 'mint';
                                const fetcherLabel =
                                  p.fetcher_used === 'async_fetcher'
                                    ? 'curl_cffi'
                                    : p.fetcher_used === 'dynamic_fetcher'
                                    ? 'Playwright'
                                    : 'Camoufox Stealth';

                                return (
                                  <Paper key={i} p="xs" radius="xs" withBorder style={{ background: 'var(--color-slate-900)', borderColor: 'var(--color-slate-800)' }}>
                                    <Group justify="space-between" wrap="nowrap">
                                      <Stack gap={2} style={{ flex: 1 }}>
                                        <Anchor href={p.url} target="_blank" size="xs" fw={500} truncate style={{ color: 'var(--color-mint-500)' }}>
                                          {p.title || p.url}
                                        </Anchor>
                                        {p.fallback_attempts && p.fallback_attempts.length > 1 && (
                                          <Group gap={4}>
                                            <ThemeIcon size="xs" color="yellow" variant="light">
                                              <IconRefresh size={10} />
                                            </ThemeIcon>
                                            <Text size="xxs" c="yellow.8" fw={500}>
                                              Fell back: {p.fallback_attempts.join(' → ')}
                                            </Text>
                                          </Group>
                                        )}
                                        {!p.success && p.error && (
                                          <Group gap={4}>
                                            <ThemeIcon size="xs" color="red" variant="light">
                                              <IconAlertTriangle size={10} />
                                            </ThemeIcon>
                                            <Text size="xxs" c="red" fw={500}>
                                              Failed: {p.error}
                                            </Text>
                                          </Group>
                                        )}
                                      </Stack>
                                      <Group gap="xs">
                                        <Badge size="xs" color={p.success ? 'mint' : 'red'} variant="filled" style={{ fontFamily: 'Fira Code' }}>
                                          {p.success ? `200` : `ERR`}
                                        </Badge>
                                        {p.success && (
                                          <Badge size="xs" color={fetcherColor} variant="light" style={{ fontFamily: 'Fira Code' }}>
                                            {fetcherLabel}
                                          </Badge>
                                        )}
                                      </Group>
                                    </Group>
                                  </Paper>
                                );
                              })}
                            </Stack>
                          </div>
                        )}

                        {/* Synthesis statistics & Confidence */}
                        {isFinished && (
                          <>
                            <Divider my="xs" style={{ borderColor: 'var(--color-slate-800)' }} />
                            <Group justify="space-between">
                              <Group gap="xs">
                                <Badge size="xs" color="blue" style={{ fontFamily: 'Fira Code' }}>{c.answerLength || 0} chars</Badge>
                                <Badge size="xs" color="mint" style={{ fontFamily: 'Fira Code' }}>{c.citationCount || 0} citations</Badge>
                                {c.planUpdated && <Badge size="xs" color="violet" style={{ fontFamily: 'Fira Code' }}>Plan updated</Badge>}
                              </Group>

                              {c.confidenceScore !== undefined && (
                                <Tooltip label={c.confidenceReasoning || ''}>
                                  <Badge
                                    size="xs"
                                    color={c.confidenceScore >= 0.7 ? 'mint' : c.confidenceScore >= 0.4 ? 'yellow' : 'red'}
                                    variant="filled"
                                    style={{ fontFamily: 'Fira Code' }}
                                  >
                                    Confidence: {Math.round(c.confidenceScore * 100)}%
                                  </Badge>
                                </Tooltip>
                              )}
                            </Group>
                          </>
                        )}
                      </Stack>
                    </Accordion.Panel>
                  </Accordion.Item>
                </Accordion>
              </Timeline.Item>
            );
          })}

          {/* Static Post-run Steps */}
          {nonCycleEvents
            .filter((ev) => ['generating_report', 'complete', 'error'].includes(ev.event))
            .map((ev, idx) => {
              const cfg = STATE_CONFIG[ev.event] || STATE_CONFIG.initializing;
              return (
                <Timeline.Item
                  key={`post-${idx}`}
                  bullet={
                    <ThemeIcon size={28} radius="xl" color={cfg.color} variant="filled">
                      <cfg.icon size={14} />
                    </ThemeIcon>
                  }
                  title={<Text size="sm" fw={500}>{cfg.label}</Text>}
                >
                  {ev.event === 'complete' && (
                    <Group gap="xs" mt={4}>
                      <Badge size="xs" color="green" variant="filled">
                        {ev.data.total_cycles || 0} cycles
                      </Badge>
                      <Badge size="xs" color="blue" variant="filled">
                        {ev.data.total_citations || 0} citations
                      </Badge>
                      {ev.data.duration_seconds && (
                        <Badge size="xs" color="gray" variant="light">
                          {Math.round(ev.data.duration_seconds)}s
                        </Badge>
                      )}
                    </Group>
                  )}
                  {ev.event === 'error' && (
                    <Alert color="red" variant="light" mt={4} p="xs">
                      <Text size="xs">{ev.data.error || 'Unknown error'}</Text>
                    </Alert>
                  )}
                </Timeline.Item>
              );
            })}
        </Timeline>

        <div ref={timelineEndRef} />
      </Paper>
    </Stack>
  );
}
