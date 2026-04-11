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
} from '@tabler/icons-react';
import type { ResearchEvent } from '../../types/api';

type Props = {
  events: ResearchEvent[];
  isActive: boolean;
};

const STATE_CONFIG: Record<
  string,
  { icon: typeof IconSearch; color: string; label: string }
> = {
  initializing: { icon: IconNetwork, color: 'gray', label: 'Initializing' },
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
  const timelineEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    for (const ev of events) {
      if (ev.data?.cycle) setCurrentCycle(ev.data.cycle);
      if (ev.data?.max_cycles) setMaxCycles(ev.data.max_cycles);
      if (ev.data?.progress) setProgressPercent(ev.data.progress);
      setCurrentState(ev.event);
    }
  }, [events]);

  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  const stateConfig = STATE_CONFIG[currentState] || STATE_CONFIG.initializing;

  // Build timeline items from key events
  const timelineEvents = events.filter((ev) =>
    [
      'planning',
      'plan_ready',
      'decomposing',
      'searching',
      'scraping',
      'validating',
      'synthesizing',
      'retrying',
      'cycle_complete',
      'confidence',
      'generating_report',
      'complete',
      'error',
      'progress',
    ].includes(ev.event)
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
                {isActive
                  ? 'Research in progress...'
                  : 'Research completed'}
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
                  value: maxCycles
                    ? (currentCycle / maxCycles) * 100
                    : 0,
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

      {/* ─── Event Timeline ────────────────────────────────── */}
      <Paper p="lg" radius="md" withBorder>
        <Title order={5} mb="md">
          Research Timeline
        </Title>

        <Timeline
          active={timelineEvents.length - 1}
          bulletSize={28}
          lineWidth={2}
        >
          {timelineEvents.map((ev, idx) => {
            const cfg =
              STATE_CONFIG[ev.event] || STATE_CONFIG.initializing;
            return (
              <Timeline.Item
                key={idx}
                bullet={
                  <ThemeIcon
                    size={28}
                    radius="xl"
                    color={cfg.color}
                    variant="filled"
                  >
                    <cfg.icon size={14} />
                  </ThemeIcon>
                }
                title={
                  <Group gap="xs">
                    <Text size="sm" fw={500}>
                      {cfg.label}
                    </Text>
                    {ev.data?.cycle && (
                      <Badge size="xs" variant="light" color="gray">
                        Cycle {ev.data.cycle}
                      </Badge>
                    )}
                  </Group>
                }
              >
                <TimelineEventDetail event={ev} />
              </Timeline.Item>
            );
          })}
        </Timeline>

        <div ref={timelineEndRef} />
      </Paper>
    </Stack>
  );
}

/** Render detail text for each event type */
function TimelineEventDetail({ event: ev }: { event: ResearchEvent }) {
  switch (ev.event) {
    case 'plan_ready':
      return (
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
      );

    case 'decomposing':
      return (
        <Text size="xs" c="dimmed" mt={4}>
          🧠 Breaking query into focused sub-queries...
        </Text>
      );

    case 'searching':
      return (
        <Text size="xs" c="dimmed" mt={4}>
          🔍 Query: <Code>{ev.data.query || '...'}</Code>
        </Text>
      );

    case 'scraping':
      return (
        <Text size="xs" c="dimmed" mt={4}>
          📄 Scraped {ev.data.successful ?? 0}/{ev.data.urls_scraped ?? 0} pages
        </Text>
      );

    case 'validating':
      if (ev.data.pages_filtered != null) {
        return (
          <Text size="xs" c="dimmed" mt={4}>
            ✅ Kept {ev.data.pages_after} pages (filtered{' '}
            {ev.data.pages_filtered})
          </Text>
        );
      }
      return null;

    case 'retrying':
      return (
        <Alert
          color="yellow"
          variant="light"
          mt={4}
          p="xs"
          icon={<IconRefresh size={14} />}
        >
          <Text size="xs">
            {ev.data.message || ev.data.error || 'Retrying...'}
          </Text>
        </Alert>
      );

    case 'cycle_complete':
      return (
        <Group gap="xs" mt={4}>
          <Badge size="xs" color="blue" variant="light">
            {ev.data.answer_length || 0} chars
          </Badge>
          <Badge size="xs" color="teal" variant="light">
            {ev.data.citation_count || 0} citations
          </Badge>
          {ev.data.plan_updated && (
            <Badge size="xs" color="violet" variant="light">
              Plan updated
            </Badge>
          )}
        </Group>
      );

    case 'confidence': {
      const score: number = ev.data.score ?? 0;
      const pct = Math.round(score * 100);
      const color = score >= 0.7 ? 'green' : score >= 0.4 ? 'yellow' : 'red';
      const emoji = score >= 0.7 ? '🟢' : score >= 0.4 ? '🟡' : '🔴';
      return (
        <Group gap="xs" mt={4}>
          <Badge size="xs" color={color} variant="light">
            {emoji} Confidence: {pct}%
          </Badge>
          {ev.data.needs_more_research && (
            <Badge size="xs" color="orange" variant="dot">
              needs more research
            </Badge>
          )}
          {ev.data.reasoning && (
            <Text size="xs" c="dimmed" style={{ fontStyle: 'italic' }}>
              {String(ev.data.reasoning).slice(0, 80)}
            </Text>
          )}
        </Group>
      );
    }

    case 'progress':
      return (
        <Group gap="xs" mt={4}>
          <Badge
            size="xs"
            color={
              ev.data.progress >= 80
                ? 'green'
                : ev.data.progress >= 50
                ? 'yellow'
                : 'orange'
            }
          >
            {ev.data.progress}% coverage
          </Badge>
        </Group>
      );

    case 'error':
      return (
        <Alert color="red" variant="light" mt={4} p="xs">
          <Text size="xs">{ev.data.error || 'Unknown error'}</Text>
        </Alert>
      );

    case 'complete':
      return (
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
      );

    default:
      return null;
  }
}
