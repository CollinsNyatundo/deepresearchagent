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
  const timelineEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const cycleMap: Record<number, CycleData> = {};
    let foundIntent = null;

    for (const ev of events) {
      if (ev.data?.max_cycles) setMaxCycles(ev.data.max_cycles);
      if (ev.data?.progress) setProgressPercent(ev.data.progress);
      setCurrentState(ev.event);

      if (ev.event === 'plan_ready' && ev.data?.intent) {
        foundIntent = ev.data.intent;
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
      <Paper p="lg" radius="md" withBorder>
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
              <Text fw={600} size="lg">
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
                  color: 'indigo',
                },
              ]}
              label={
                <Text ta="center" size="xs" fw={700}>
                  {currentCycle}/{maxCycles}
                </Text>
              }
            />
          )}
        </Group>

        {maxCycles > 0 && (
          <Progress
            value={maxCycles ? (currentCycle / maxCycles) * 100 : 0}
            color="indigo"
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
        <Paper p="lg" radius="md" withBorder>
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

      {/* ─── Event Timeline ────────────────────────────────── */}
      <Paper p="lg" radius="md" withBorder>
        <Title order={5} mb="md">
          Research Timeline
        </Title>

        <Timeline bulletSize={28} lineWidth={2} active={cycles.length + nonCycleEvents.length - 1}>
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
            const color = isFinished ? 'green' : 'blue';

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
                    <Text size="sm" fw={600}>
                      Cycle {c.cycle}
                    </Text>
                    {c.isSearching && <Badge size="xs" color="blue">Searching</Badge>}
                    {c.isScraping && <Badge size="xs" color="orange">Scraping</Badge>}
                    {c.isValidating && <Badge size="xs" color="teal">Filtering</Badge>}
                    {c.isSynthesizing && <Badge size="xs" color="indigo">Synthesizing</Badge>}
                    {c.isReflecting && <Badge size="xs" color="purple">Reflecting</Badge>}
                    {isFinished && <Badge size="xs" color="green">Complete</Badge>}
                  </Group>
                }
              >
                <Accordion variant="separated" mt="xs">
                  <Accordion.Item value="details">
                    <Accordion.Control>
                      <Text size="xs" fw={500} c="dimmed">
                        {c.query ? `Query: "${c.query.slice(0, 60)}..."` : 'Details & Scraped Contents'}
                      </Text>
                    </Accordion.Control>
                    <Accordion.Panel>
                      <Stack gap="sm">
                        {c.query && (
                          <div>
                            <Text size="xs" fw={600} c="dimmed" mb={2}>🔍 Search Query:</Text>
                            <Code block>{c.query}</Code>
                          </div>
                        )}

                        {/* Pointwise AutoEval Search relevance List */}
                        {c.search_results && c.search_results.length > 0 && (
                          <div>
                            <Text size="xs" fw={600} c="dimmed" mb={4}>🎯 snippet AutoEval Relevance Scores:</Text>
                            <Stack gap={6}>
                              {c.search_results.map((r, i) => {
                                const score = r.relevance_score ?? 1.0;
                                const passed = score >= 0.7;
                                return (
                                  <Paper key={i} p="xs" withBorder radius="xs" style={{ background: '#fafafa' }}>
                                    <Group justify="space-between" align="flex-start" wrap="nowrap">
                                      <Stack gap={2} style={{ flex: 1 }}>
                                        <Anchor href={r.url} target="_blank" size="xs" fw={500} truncate>
                                          {r.title || r.url}
                                        </Anchor>
                                        <Text size="xxs" c="dimmed" lineClamp={2}>
                                          {r.snippet}
                                        </Text>
                                        {r.eval_rationale && (
                                          <Text size="xxs" style={{ fontStyle: 'italic' }} c="dimmed">
                                            Judge: {r.eval_rationale}
                                          </Text>
                                        )}
                                      </Stack>
                                      <Badge size="xs" color={passed ? 'green' : 'red'}>
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
                            <Text size="xs" fw={600} c="dimmed" mb={4}>📄 Scraped Content Fallbacks & Status:</Text>
                            <Stack gap={4}>
                              {c.scraped_pages.map((p, i) => {
                                const fetcherColor =
                                  p.fetcher_used === 'async_fetcher'
                                    ? 'green'
                                    : p.fetcher_used === 'dynamic_fetcher'
                                    ? 'orange'
                                    : 'indigo';
                                const fetcherLabel =
                                  p.fetcher_used === 'async_fetcher'
                                    ? 'curl_cffi'
                                    : p.fetcher_used === 'dynamic_fetcher'
                                    ? 'Playwright'
                                    : 'Camoufox Stealth';

                                return (
                                  <Paper key={i} p="xs" radius="xs" withBorder>
                                    <Group justify="space-between" wrap="nowrap">
                                      <Stack gap={2} style={{ flex: 1 }}>
                                        <Anchor href={p.url} target="_blank" size="xs" fw={500} truncate>
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
                                        <Badge size="xs" color={p.success ? 'green' : 'red'}>
                                          {p.success ? `200` : `ERR`}
                                        </Badge>
                                        {p.success && (
                                          <Badge size="xs" color={fetcherColor}>
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
                            <Divider my="xs" />
                            <Group justify="space-between">
                              <Group gap="xs">
                                <Badge size="xs" color="blue">{c.answerLength || 0} chars</Badge>
                                <Badge size="xs" color="teal">{c.citationCount || 0} citations</Badge>
                                {c.planUpdated && <Badge size="xs" color="violet">Plan updated</Badge>}
                              </Group>

                              {c.confidenceScore !== undefined && (
                                <Tooltip label={c.confidenceReasoning || ''}>
                                  <Badge
                                    size="xs"
                                    color={c.confidenceScore >= 0.7 ? 'green' : c.confidenceScore >= 0.4 ? 'yellow' : 'red'}
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
