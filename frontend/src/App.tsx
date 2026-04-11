import { useState, useCallback, useRef, useEffect } from 'react';
import { useDisclosure } from '@mantine/hooks';
import {
  AppShell,
  Burger,
  Group,
  Title,
  Text,
  Tabs,
  Stack,
  Button,
  Modal,
  TextInput,
  Textarea,
  Slider,
  Tooltip,
  Badge,
  Notification,
  Select,
  Loader,
  SegmentedControl,
} from '@mantine/core';
import {
  IconFlask,
  IconMap,
  IconFileText,
  IconPlus,
  IconBrain,
  IconDownload,
  IconListCheck,
  IconNetwork,
  IconCode,
} from '@tabler/icons-react';

import { RunList } from './components/runs/RunList';
import { ReportView } from './components/views/ReportView';
import { MindmapView } from './components/views/MindmapView';
import { KnowledgeGraphView } from './components/knowledge-graph/KnowledgeGraphView';
import { ResearchProgress } from './components/views/ResearchProgress';
import { PlanReview } from './components/views/PlanReview';
import { ExportPanel } from './components/views/ExportPanel';
import { api } from './api/client';
import type { ResearchEvent, PlanPreview } from './types/api';

const OPENROUTER_PRESETS = [
  {
    value: 'nvidia/nemotron-3-super-120b-a12b:free',
    label: 'Nemotron 3 Super — 1M ctx, agents',
  },
  {
    value: 'openai/gpt-oss-120b:free',
    label: 'GPT-OSS 120B — general reasoning',
  },
  {
    value: 'qwen/qwen3-235b-a22b:free',
    label: 'Qwen 3 235B — RAG + tools',
  },
];

const GROQ_PRESETS = [
  {
    value: 'llama-3.3-70b-versatile',
    label: 'Llama 3.3 70B — best for research/agents',
  },
  {
    value: 'deepseek-r1-distill-llama-70b',
    label: 'DeepSeek R1 (Llama 70B) — reasoning',
  },
  {
    value: 'llama-3.1-8b-instant',
    label: 'Llama 3.1 8B Instant — fastest',
  },
];

type AppState =
  | 'idle'           // No research selected
  | 'modal'          // New research modal open (query input)
  | 'plan_loading'   // Generating plan
  | 'plan_review'    // User reviewing/editing plan
  | 'streaming'      // Research in progress with SSE
  | 'results';       // Viewing completed results

export default function App() {
  const [navOpened, { toggle: toggleNav }] = useDisclosure(true);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string | null>('report');
  const [refreshKey, setRefreshKey] = useState(0);

  // Global view: 'research' | 'code-arch'
  const [globalView, setGlobalView] = useState<'research' | 'code-arch'>('research');

  // GitNexus repo selection
  const [gitnexusRepos, setGitnexusRepos] = useState<string[]>([]);
  const [selectedGitnexusRepo, setSelectedGitnexusRepo] = useState<string | null>(null);
  const [gitnexusReposLoading, setGitnexusReposLoading] = useState(false);

  // Load repo list when switching to Code Arch view
  useEffect(() => {
    if (globalView !== 'code-arch') return;
    setGitnexusReposLoading(true);
    api.listGitnexusRepos()
      .then(({ repos }) => {
        setGitnexusRepos(repos);
        if (repos.length > 0 && !selectedGitnexusRepo) {
          setSelectedGitnexusRepo(repos[0]);
        }
      })
      .catch(() => setGitnexusRepos([]))
      .finally(() => setGitnexusReposLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [globalView]);

  // App state machine
  const [appState, setAppState] = useState<AppState>('idle');

  // New research modal
  const [modalOpen, { open: openModal, close: closeModal }] = useDisclosure(false);
  const [query, setQuery] = useState('');
  const [model, setModel] = useState('nvidia/nemotron-3-super-120b-a12b:free');
  const [provider, setProvider] = useState<'openrouter' | 'groq'>('openrouter');
  const [depth, setDepth] = useState(5);
  const [mode, setMode] = useState<'web' | 'github'>('web');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // When provider changes, reset model to the best default for that provider
  const handleProviderChange = (val: string) => {
    const p = val as 'openrouter' | 'groq';
    setProvider(p);
    if (p === 'groq') {
      setModel('llama-3.3-70b-versatile');
    } else {
      setModel('nvidia/nemotron-3-super-120b-a12b:free');
    }
  };

  // Plan review state (Phase 4)
  const [planPreview, setPlanPreview] = useState<PlanPreview | null>(null);
  const [planQuery, setPlanQuery] = useState('');

  // SSE streaming state (Phase 2)
  const [streamEvents, setStreamEvents] = useState<ResearchEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Knowledge graph state (Graphify)
  const [kgReady, setKgReady] = useState(false);
  const [kgStats, setKgStats] = useState<{ nodes: number; edges: number; communities: number } | null>(null);

  // ─── Generate Plan (Phase 4) ──────────────────────────────
  const handleGeneratePlan = useCallback(async () => {
    if (!query.trim()) return;
    setIsSubmitting(true);
    setError(null);
    setAppState('plan_loading');

    try {
      const preview = await api.generatePlan({
        query: query.trim(),
        model,
        depth,
        mode,
        provider,
      });
      setPlanPreview(preview);
      setPlanQuery(query.trim());
      setAppState('plan_review');
      closeModal();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Plan generation failed');
      setAppState('modal');
    } finally {
      setIsSubmitting(false);
    }
  }, [query, model, depth, mode, provider, closeModal]);

  // ─── Approve & Start Research with SSE (Phase 2 + Phase 4) ─
  const handleApproveAndStart = useCallback(
    (steps: string[], subQueries: string[], exportFormats: string[]) => {
      setStreamEvents([]);
      setIsStreaming(true);
      setAppState('streaming');
      setActiveTab('progress');
      setKgReady(false);
      setKgStats(null);

      const controller = api.streamApprovedPlan(
        {
          query: planQuery,
          plan: { steps },
          sub_queries: subQueries,
          model,
          depth,
          mode,
          provider,
          export_formats: exportFormats,
        },
        // onEvent
        (event) => {
          setStreamEvents((prev) => [...prev, event]);
          // Handle knowledge graph ready event
          if (event.event === 'knowledge_graph_ready') {
            setKgReady(true);
            setKgStats({
              nodes: event.data.node_count ?? 0,
              edges: event.data.edge_count ?? 0,
              communities: event.data.community_count ?? 0,
            });
          }
        },
        // onDone
        (data) => {
          setIsStreaming(false);
          if (data.run_id) {
            setSelectedRunId(data.run_id);
            setRefreshKey((k) => k + 1);
            setActiveTab('report');
            setAppState('results');
          }
        },
        // onError
        (errorMsg) => {
          setIsStreaming(false);
          setError(errorMsg);
        },
      );

      abortRef.current = controller;
    },
    [planQuery, model, depth, mode, provider],
  );

  // ─── Quick Start (no plan review — direct SSE stream) ─────
  const handleQuickStart = useCallback(async () => {
    if (!query.trim()) return;
    setIsSubmitting(true);
    setError(null);
    closeModal();
    setStreamEvents([]);
    setIsStreaming(true);
    setAppState('streaming');
    setActiveTab('progress');

    const controller = api.streamResearch(
      {
        query: query.trim(),
        model,
        depth,
        mode,
        provider,
      },
      (event) => {
        setStreamEvents((prev) => [...prev, event]);
        if (event.event === 'knowledge_graph_ready') {
          setKgReady(true);
          setKgStats({
            nodes: event.data.node_count ?? 0,
            edges: event.data.edge_count ?? 0,
            communities: event.data.community_count ?? 0,
          });
        }
      },
      (data) => {
        setIsStreaming(false);
        setIsSubmitting(false);
        if (data.run_id) {
          setSelectedRunId(data.run_id);
          setRefreshKey((k) => k + 1);
          setActiveTab('report');
          setAppState('results');
        }
      },
      (errorMsg) => {
        setIsStreaming(false);
        setIsSubmitting(false);
        setError(errorMsg);
      },
    );

    abortRef.current = controller;
    setQuery('');
  }, [query, model, depth, mode, provider, closeModal]);

  // ─── Reset to idle ────────────────────────────────────────
  const resetToIdle = useCallback(() => {
    setPlanPreview(null);
    setPlanQuery('');
    setStreamEvents([]);
    setIsStreaming(false);
    setKgReady(false);
    setKgStats(null);
    setAppState('idle');
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{
        width: 300,
        breakpoint: 'sm',
        collapsed: { mobile: !navOpened },
      }}
      padding="md"
    >
      {/* ─── Header ─────────────────────────────────────────── */}
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger
              opened={navOpened}
              onClick={toggleNav}
              hiddenFrom="sm"
              size="sm"
            />
            <IconBrain size={30} color="var(--mantine-color-indigo-6)" />
            <Title order={3} visibleFrom="xs">
              Deep Research Agent
            </Title>
          </Group>
          <Group>
            {isStreaming && (
              <Badge variant="dot" color="green" size="lg">
                Researching...
              </Badge>
            )}
            <Badge variant="light" color={provider === 'groq' ? 'orange' : 'indigo'} size="lg">
              {provider === 'groq' ? 'Groq: ' : ''}{model.split('/').pop()?.replace(/:.*$/, '') || 'model'}
            </Badge>
          </Group>
        </Group>
      </AppShell.Header>

      {/* ─── Sidebar ─────────────────────────────────────────── */}
      <AppShell.Navbar p="md">
        <Stack gap="sm" style={{ height: '100%' }}>
          {/* Mode switcher */}
          <SegmentedControl
            fullWidth
            size="xs"
            value={globalView}
            onChange={(val) => setGlobalView(val as 'research' | 'code-arch')}
            data={[
              { label: 'Research', value: 'research' },
              { label: 'Code Arch', value: 'code-arch' },
            ]}
          />
          {globalView === 'research' && (
            <>
              <Button
                fullWidth
                leftSection={<IconPlus size={18} />}
                onClick={() => {
                  resetToIdle();
                  openModal();
                }}
                variant="gradient"
                gradient={{ from: 'indigo', to: 'violet', deg: 135 }}
              >
                New Research
              </Button>
              <RunList
                key={refreshKey}
                selectedRunId={selectedRunId}
                onSelectRun={(id) => {
                  resetToIdle();
                  setSelectedRunId(id);
                  setActiveTab('report');
                  setAppState('results');
                }}
              />
            </>
          )}
          {globalView === 'code-arch' && (
            <Stack gap="sm">
              <Text size="xs" fw={600} c="dimmed">REPOSITORY</Text>
              {gitnexusReposLoading ? (
                <Loader size="xs" />
              ) : gitnexusRepos.length === 0 ? (
                <Text size="xs" c="red">
                  Eval-server not running.<br />
                  Start with:<br />
                  <code>npx gitnexus eval-server --port 4848</code>
                </Text>
              ) : (
                <Select
                  size="sm"
                  placeholder="Select repo…"
                  data={gitnexusRepos.map((r) => ({ value: r, label: r }))}
                  value={selectedGitnexusRepo}
                  onChange={setSelectedGitnexusRepo}
                />
              )}
              <Text size="xs" c="dimmed">
                GitNexus codebase intelligence — refreshes every 30 min automatically.
              </Text>
            </Stack>
          )}
        </Stack>
      </AppShell.Navbar>

      {/* ─── Main Content ───────────────────────────────────── */}
      <AppShell.Main>
        {/* Plan Review Mode */}
        {appState === 'plan_review' && planPreview && (
          <PlanReview
            preview={planPreview}
            query={planQuery}
            onApprove={handleApproveAndStart}
            onRegenerate={() => {
              setAppState('modal');
              openModal();
            }}
            isLoading={isSubmitting}
          />
        )}

        {/* Plan Loading */}
        {appState === 'plan_loading' && (
          <Stack align="center" justify="center" style={{ height: '60vh' }}>
            <Loader size="xl" color="indigo" />
            <Title order={3} c="dimmed">
              Generating Research Plan...
            </Title>
            <Text c="dimmed">The AI is creating a comprehensive plan for your query.</Text>
          </Stack>
        )}

        {/* SSE Streaming Mode */}
        {appState === 'streaming' && (
          <ResearchProgress events={streamEvents} isActive={isStreaming} />
        )}

        {/* Results Mode (existing tabs) */}
        {(appState === 'results' || appState === 'idle') && selectedRunId && (
          <Stack gap="md">
            <Tabs value={activeTab} onChange={setActiveTab}>
              <Tabs.List>
                <Tabs.Tab
                  value="report"
                  leftSection={<IconFileText size={16} />}
                >
                  Report
                </Tabs.Tab>
                <Tabs.Tab
                  value="mindmap"
                  leftSection={<IconMap size={16} />}
                >
                  Mindmap
                </Tabs.Tab>
                <Tabs.Tab
                  value="knowledge-graph"
                  leftSection={<IconNetwork size={16} />}
                  rightSection={
                    kgReady ? (
                      <Badge size="xs" color="teal" variant="filled" circle>
                        ✓
                      </Badge>
                    ) : undefined
                  }
                >
                  Knowledge Graph
                  {kgStats && (
                    <Text span size="xs" c="dimmed" ml={4}>
                      ({kgStats.nodes}N)
                    </Text>
                  )}
                </Tabs.Tab>
                <Tabs.Tab
                  value="export"
                  leftSection={<IconDownload size={16} />}
                >
                  Export
                </Tabs.Tab>
              </Tabs.List>

              <Tabs.Panel value="report" pt="md">
                <ReportView runId={selectedRunId} />
              </Tabs.Panel>
              <Tabs.Panel value="mindmap" pt="md">
                <MindmapView runId={selectedRunId} />
              </Tabs.Panel>
              <Tabs.Panel value="knowledge-graph" pt="md">
                <KnowledgeGraphView runId={selectedRunId} />
              </Tabs.Panel>
              <Tabs.Panel value="export" pt="md">
                <ExportPanel runId={selectedRunId} />
              </Tabs.Panel>
            </Tabs>
          </Stack>
        )}

        {/* Idle — no run selected */}
        {appState === 'idle' && !selectedRunId && (
          <Stack align="center" justify="center" style={{ height: '60vh' }}>
            <IconFlask size={80} color="var(--mantine-color-gray-3)" stroke={1} />
            <Title order={2} c="dimmed">
              Deep Research Agent
            </Title>
            <Text c="dimmed" ta="center" maw={500} size="lg">
              Select a past research run from the sidebar, or start a new
              exhaustive research with the button above.
            </Text>
            <Button
              size="lg"
              variant="gradient"
              gradient={{ from: 'indigo', to: 'violet', deg: 135 }}
              leftSection={<IconPlus size={20} />}
              onClick={openModal}
              mt="md"
            >
              Start New Research
            </Button>
          </Stack>
        )}

        {/* Global error banner */}
        {error && appState !== 'modal' && (
          <Notification
            color="red"
            title="Error"
            onClose={() => setError(null)}
            mt="md"
          >
            {error}
          </Notification>
        )}

        {/* ─── Code Architecture View (GitNexus) ─────────────── */}
        {globalView === 'code-arch' && (
          <Stack gap="md">
            <Group>
              <IconCode size={24} color="var(--mantine-color-violet-6)" />
              <Title order={3}>Code Architecture</Title>
              {selectedGitnexusRepo && (
                <Badge variant="light" color="violet">{selectedGitnexusRepo}</Badge>
              )}
              <Badge variant="outline" color="gray">GitNexus</Badge>
            </Group>
            <Text c="dimmed" size="sm">
              Interactive codebase topology — nodes are Files, Classes, and Functions;
              edges are CALLS, IMPORTS, EXTENDS relationships extracted from the live code graph.
              {!selectedGitnexusRepo && ' Select a repository from the sidebar to begin.'}
            </Text>
            {selectedGitnexusRepo ? (
              <KnowledgeGraphView
                runId={`gitnexus:${selectedGitnexusRepo}`}
                gitnexusRepo={selectedGitnexusRepo}
              />
            ) : (
              <Stack align="center" justify="center" style={{ height: '40vh' }} gap="lg">
                <IconCode size={48} color="var(--mantine-color-dimmed)" />
                <Text c="dimmed">No repository selected. Choose one from the sidebar.</Text>
              </Stack>
            )}
          </Stack>
        )}
      </AppShell.Main>

      {/* ─── New Research Modal ─────────────────────────────── */}
      <Modal
        opened={modalOpen}
        onClose={closeModal}
        title={
          <Group>
            <IconFlask size={24} color="var(--mantine-color-indigo-6)" />
            <Title order={4}>New Research</Title>
          </Group>
        }
        size="lg"
      >
        <Stack gap="md">
          <Textarea
            label="Research Query"
            placeholder="What do you want to research? Be specific for better results."
            description="The engine will create a research plan and iterate through multiple search + scraping cycles."
            minRows={3}
            autosize
            maxRows={6}
            value={query}
            onChange={(e) => setQuery(e.currentTarget.value)}
            required
          />

          <div>
            <Text size="sm" fw={500} mb={4}>
              LLM Provider
            </Text>
            <SegmentedControl
              fullWidth
              value={provider}
              onChange={handleProviderChange}
              data={[
                { label: '🌐 OpenRouter (free models)', value: 'openrouter' },
                { label: '⚡ Groq (fast inference)', value: 'groq' },
              ]}
            />
          </div>

          <div>
            <Text size="sm" fw={500} mb={4}>
              Domain
            </Text>
            <SegmentedControl
              fullWidth
              value={mode}
              onChange={(val) => setMode(val as 'web' | 'github')}
              data={[
                { label: 'Web Research', value: 'web' },
                { label: 'GitHub Repository', value: 'github' },
              ]}
            />
          </div>

          <Tooltip
            label={provider === 'groq'
              ? 'Enter a Groq model ID (e.g. llama-3.3-70b-versatile). See console.groq.com for available models.'
              : 'Paste any OpenRouter model ID. The model handles planning, synthesis, and report generation.'}
            multiline
            maw={400}
          >
            <TextInput
              label={provider === 'groq' ? 'Model (Groq ID)' : 'Model (OpenRouter ID)'}
              placeholder={provider === 'groq' ? 'llama-3.3-70b-versatile' : 'nvidia/nemotron-3-super-120b-a12b:free'}
              description={provider === 'groq' ? 'Groq model name — no provider prefix needed' : 'Supports any model available on OpenRouter'}
              value={model}
              onChange={(e) => setModel(e.currentTarget.value)}
            />
          </Tooltip>

          <Select
            label="Quick Presets"
            placeholder="Select a preset model..."
            data={provider === 'groq' ? GROQ_PRESETS : OPENROUTER_PRESETS}
            onChange={(val) => val && setModel(val)}
            clearable
          />

          <div>
            <Text size="sm" fw={500} mb={8}>
              Depth: {depth}{' '}
              <Text span c="dimmed" size="xs">
                ({depth === 1
                  ? 'Quick — 6 cycles'
                  : depth === 3
                  ? 'Standard — 18 cycles'
                  : depth === 5
                  ? 'Exhaustive — 30 cycles'
                  : `${depth * 6} cycles`})
              </Text>
            </Text>
            <Slider
              min={1}
              max={5}
              step={1}
              value={depth}
              onChange={setDepth}
              marks={[
                { value: 1, label: 'Quick' },
                { value: 3, label: 'Standard' },
                { value: 5, label: 'Exhaustive' },
              ]}
              mb="lg"
            />
          </div>

          {error && (
            <Notification
              color="red"
              title="Error"
              onClose={() => setError(null)}
            >
              {error}
            </Notification>
          )}

          <Group grow>
            <Button
              size="md"
              loading={isSubmitting}
              onClick={handleGeneratePlan}
              disabled={!query.trim()}
              variant="gradient"
              gradient={{ from: 'indigo', to: 'violet', deg: 135 }}
              leftSection={<IconListCheck size={18} />}
            >
              Generate Plan
            </Button>
            <Button
              size="md"
              loading={isSubmitting}
              onClick={handleQuickStart}
              disabled={!query.trim()}
              variant="light"
              color="indigo"
              leftSection={<IconFlask size={18} />}
            >
              Quick Start
            </Button>
          </Group>
        </Stack>
      </Modal>
    </AppShell>
  );
}
