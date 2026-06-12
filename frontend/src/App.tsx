import { useState, useCallback, useRef, useEffect } from 'react';
import { useDisclosure } from '@mantine/hooks';
import {
  AppShell,
  Anchor,
  Box,
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
  Paper,
} from '@mantine/core';
import {
  IconFlask,
  IconPlus,
  IconBrain,
  IconDownload,
  IconListCheck,
  IconQuote,
} from '@tabler/icons-react';

import { RunList } from './components/runs/RunList';
import { ReportView } from './components/views/ReportView';
import { CitationsView } from './components/views/CitationsView';
import { GitNexusWebView } from './components/code-arch/GitNexusWebView';
import { ResearchProgress } from './components/views/ResearchProgress';
import { PlanReview } from './components/views/PlanReview';
import { ExportPanel } from './components/views/ExportPanel';
import { TerminalDemo } from './components/landing/TerminalDemo';
import { api } from './api/client';
import type { ResearchEvent, PlanPreview, TelemetryResponse } from './types/api';

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

const PRESETS = [
  {
    label: '⚡ Superconductivity',
    query: 'What are the latest breakthroughs in high-temperature superconductors?',
    provider: 'openrouter',
    model: 'nvidia/nemotron-3-super-120b-a12b:free',
    depth: 3,
    mode: 'web',
  },
  {
    label: '🦙 Llama Spec',
    query: 'Analyze Llama 3.3 70B performance compared to Claude 3.5 Sonnet',
    provider: 'groq',
    model: 'llama-3.3-70b-versatile',
    depth: 2,
    mode: 'web',
  },
  {
    label: '📘 TS Decorators',
    query: 'Explain TypeScript 5.0 decorators and provide comparison to stage 2 decorators',
    provider: 'openrouter',
    model: 'qwen/qwen3-235b-a22b:free',
    depth: 1,
    mode: 'web',
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
  const [activeTab, setActiveTab] = useState<string | null>('citations');
  const [refreshKey, setRefreshKey] = useState(0);

  // Global view: 'research' | 'code-arch'
  const [globalView, setGlobalView] = useState<'research' | 'code-arch'>('research');

  // App state machine
  const [appState, setAppState] = useState<AppState>('idle');

  // New research modal
  const [modalOpen, { close: closeModal }] = useDisclosure(false);
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

  // Local Telemetry stats (Task 3)
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);

  const fetchTelemetry = useCallback(async () => {
    try {
      const data = await api.getTelemetry();
      setTelemetry(data);
    } catch (err) {
      console.error('Failed to fetch telemetry:', err);
    }
  }, []);

  // Fetch telemetry on load and on transition back to idle
  useEffect(() => {
    if (appState === 'idle' && !selectedRunId) {
      fetchTelemetry();
    }
  }, [appState, selectedRunId, fetchTelemetry]);

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
        },
        // onDone
        (data) => {
          setIsStreaming(false);
          if (data.run_id) {
            setSelectedRunId(data.run_id);
            setRefreshKey((k) => k + 1);
            setActiveTab('citations');
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
      },
      (data) => {
        setIsStreaming(false);
        setIsSubmitting(false);
        if (data.run_id) {
          setSelectedRunId(data.run_id);
          setRefreshKey((k) => k + 1);
          setActiveTab('citations');
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
    setAppState('idle');
    setSelectedRunId(null);
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{
        width: 280,
        breakpoint: 'sm',
        collapsed: { mobile: !navOpened },
      }}
      padding="md"
      styles={{
        header: {
          backgroundColor: 'var(--color-slate-900)',
          borderBottom: '1px solid var(--color-slate-800)',
          color: 'var(--color-text-main)',
        },
        navbar: {
          backgroundColor: 'var(--color-slate-900)',
          borderRight: '1px solid var(--color-slate-800)',
          color: 'var(--color-text-main)',
        },
        main: {
          backgroundColor: 'var(--color-slate-950)',
          color: 'var(--color-text-main)',
          minHeight: '100vh',
        }
      }}
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
            <IconBrain size={28} color="var(--color-mint-500)" />
            <Title order={3} visibleFrom="xs" style={{ fontFamily: 'Fira Sans', fontWeight: 700, letterSpacing: '-0.02em' }}>
              DeepResearch<span style={{ color: 'var(--color-mint-500)' }}>.ai</span>
            </Title>
          </Group>
          <Group>
            {isStreaming && (
              <Badge variant="dot" color="green" size="lg">
                Researching...
              </Badge>
            )}
            <Badge variant="light" color={provider === 'groq' ? 'orange' : 'teal'} size="lg">
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
            styles={{
              root: { backgroundColor: 'var(--color-slate-950)' }
            }}
          />
          {globalView === 'research' && (
            <>
              <Button
                fullWidth
                leftSection={<IconPlus size={18} />}
                onClick={resetToIdle}
                color="mint"
              >
                New Research
              </Button>
              <RunList
                key={refreshKey}
                selectedRunId={selectedRunId}
                onSelectRun={(id) => {
                  resetToIdle();
                  setSelectedRunId(id);
                  setActiveTab('citations');
                  setAppState('results');
                }}
              />
            </>
          )}
          {globalView === 'code-arch' && (
            <Stack gap="xs" pt="xs">
              <Text size="xs" fw={600} c="dimmed">GITNEXUS WEB UI</Text>
              <Text size="xs" c="dimmed">
                The official interactive graph at{' '}
                <Anchor href="https://gitnexus.vercel.app" target="_blank" size="xs" c="mint">
                  gitnexus.vercel.app
                </Anchor>
                {' '}auto-connects to your local codebase via the bridge server on port 4747.
              </Text>
              <Text size="xs" c="dimmed">
                Click <strong>Start Local Server</strong> in the main panel to begin.
              </Text>
            </Stack>
          )}
        </Stack>
      </AppShell.Navbar>

      {/* ─── Main Content ───────────────────────────────────── */}
      <AppShell.Main>
        {/* Plan Review Mode */}
        {globalView !== 'code-arch' && appState === 'plan_review' && planPreview && (
          <PlanReview
            preview={planPreview}
            query={planQuery}
            onApprove={handleApproveAndStart}
            onRegenerate={() => {
              setAppState('idle');
            }}
            isLoading={isSubmitting}
          />
        )}

        {/* Plan Loading */}
        {globalView !== 'code-arch' && appState === 'plan_loading' && (
          <Stack align="center" justify="center" style={{ height: '60vh' }}>
            <Loader size="xl" color="mint" />
            <Title order={3} c="dimmed">
              Generating Research Plan...
            </Title>
            <Text c="dimmed">The AI is creating a comprehensive plan for your query.</Text>
          </Stack>
        )}

        {/* SSE Streaming Mode */}
        {globalView !== 'code-arch' && appState === 'streaming' && (
          <ResearchProgress events={streamEvents} isActive={isStreaming} />
        )}

        {/* Results Mode (Split Three-Pane Layout) */}
        {(appState === 'results' || appState === 'idle') && selectedRunId && globalView !== 'code-arch' && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
            gap: '24px',
            height: 'calc(100vh - 100px)',
            overflow: 'hidden'
          }}>
            {/* Left Column: Markdown Report */}
            <div style={{ overflowY: 'auto', paddingRight: '4px' }}>
              <ReportView runId={selectedRunId} />
            </div>

            {/* Right Column: Mindmap, Graph, and Export Controls */}
            <div style={{
              overflowY: 'auto',
              borderLeft: '1px solid var(--color-slate-800)',
              paddingLeft: '24px',
              height: '100%'
            }}>
              <Tabs value={activeTab} onChange={setActiveTab}>
                <Tabs.List mb="md" styles={{
                  list: { borderColor: 'var(--color-slate-800)' }
                }}>
                  <Tabs.Tab
                    value="citations"
                    leftSection={<IconQuote size={16} />}
                  >
                    Citations
                  </Tabs.Tab>
                  <Tabs.Tab
                    value="export"
                    leftSection={<IconDownload size={16} />}
                  >
                    Export
                  </Tabs.Tab>
                </Tabs.List>

                <Tabs.Panel value="citations" pt="xs" style={{ height: 'calc(100% - 60px)' }}>
                  <CitationsView runId={selectedRunId} />
                </Tabs.Panel>
                <Tabs.Panel value="export" pt="xs">
                  <ExportPanel runId={selectedRunId} />
                </Tabs.Panel>
              </Tabs>
            </div>
          </div>
        )}

        {/* Idle — Developer Console Landing Hero */}
        {appState === 'idle' && !selectedRunId && globalView !== 'code-arch' && (
          <Stack gap="xl" align="center" style={{ maxWidth: 800, margin: '60px auto 0 auto', width: '100%' }}>
            <Stack gap={6} align="center">
              <Title order={1} style={{ fontFamily: 'Fira Sans', fontSize: '2.5rem', fontWeight: 800, letterSpacing: '-0.03em' }}>
                Deep Research <span style={{ color: 'var(--color-mint-500)' }}>Engine</span>
              </Title>
              <Text size="lg" c="dimmed" ta="center" style={{ maxWidth: 600 }}>
                Autonomous Web-Scale Scraper & Citation Compiler
              </Text>
            </Stack>

            <Paper p="xl" withBorder style={{ width: '100%', backgroundColor: 'var(--color-slate-900)', borderColor: 'var(--color-slate-800)' }}>
              <Stack gap="md">
                <Textarea
                  label="Research Objective"
                  placeholder="research_engine --query 'What are the latest breakthroughs in high-temperature superconductors?'"
                  minRows={3}
                  autosize
                  maxRows={6}
                  value={query}
                  onChange={(e) => setQuery(e.currentTarget.value)}
                  required
                  styles={{
                    input: {
                      fontFamily: 'Fira Code',
                      backgroundColor: 'var(--color-slate-950)',
                      borderColor: 'var(--color-slate-800)',
                      color: 'var(--color-text-main)',
                      fontSize: '0.95rem',
                      '&:focus': {
                        borderColor: 'var(--color-mint-500)',
                      }
                    }
                  }}
                />

                <Group gap="xs" mt={-4}>
                  {PRESETS.map((preset, idx) => (
                    <Badge
                      key={idx}
                      variant="outline"
                      color="mint"
                      style={{ cursor: 'pointer', textTransform: 'none' }}
                      onClick={() => {
                        setQuery(preset.query);
                        setProvider(preset.provider as 'openrouter' | 'groq');
                        setMode(preset.mode as 'web' | 'github');
                        setModel(preset.model);
                        setDepth(preset.depth);
                      }}
                    >
                      {preset.label}
                    </Badge>
                  ))}
                </Group>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '15px' }}>
                  <div>
                    <Text size="xs" fw={600} mb={6} c="dimmed">LLM PROVIDER</Text>
                    <SegmentedControl
                      fullWidth
                      value={provider}
                      onChange={handleProviderChange}
                      data={[
                        { label: '🌐 OpenRouter', value: 'openrouter' },
                        { label: '⚡ Groq', value: 'groq' },
                      ]}
                      styles={{
                        root: { backgroundColor: 'var(--color-slate-950)' }
                      }}
                    />
                  </div>

                  <div>
                    <Text size="xs" fw={600} mb={6} c="dimmed">TARGET CORPUS</Text>
                    <SegmentedControl
                      fullWidth
                      value={mode}
                      onChange={(val) => setMode(val as 'web' | 'github')}
                      data={[
                        { label: '🌐 Web-Scale Scrape', value: 'web' },
                        { label: '📁 Local Repository', value: 'github' },
                      ]}
                      styles={{
                        root: { backgroundColor: 'var(--color-slate-950)' }
                      }}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '15px' }}>
                  <TextInput
                    label="Inference Model ID"
                    value={model}
                    onChange={(e) => setModel(e.currentTarget.value)}
                    styles={{
                      input: {
                        fontFamily: 'Fira Code',
                        backgroundColor: 'var(--color-slate-950)',
                        borderColor: 'var(--color-slate-800)',
                        fontSize: '0.85rem',
                      }
                    }}
                  />

                  <div>
                    <Text size="xs" fw={600} mb={8} c="dimmed">
                      Search Depth (Max Scrape Rounds): {depth} ({depth === 1 ? 'Quick — 6 rounds' : depth === 3 ? 'Standard — 18 rounds' : 'Exhaustive — 30 rounds'})
                    </Text>
                    <Slider
                      min={1}
                      max={5}
                      step={1}
                      value={depth}
                      onChange={setDepth}
                      marks={[
                        { value: 1, label: 'Quick (6 rounds)' },
                        { value: 3, label: 'Standard (18 rounds)' },
                        { value: 5, label: 'Exhaustive (30 rounds)' },
                      ]}
                    />
                  </div>
                </div>

                <Group mt="md" grow>
                  <Button
                    size="md"
                    loading={isSubmitting}
                    onClick={handleGeneratePlan}
                    disabled={!query.trim()}
                    color="mint"
                    leftSection={<IconListCheck size={18} />}
                  >
                    Generate Plan
                  </Button>
                  <Button
                    size="md"
                    loading={isSubmitting}
                    onClick={handleQuickStart}
                    disabled={!query.trim()}
                    variant="outline"
                    color="mint"
                    leftSection={<IconFlask size={18} />}
                  >
                    Quick Start
                  </Button>
                </Group>
              </Stack>
            </Paper>

            {/* Bento Section: Terminal typing demo & local telemetry */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px', width: '100%', marginTop: '12px' }}>
              {/* Monospace Simulated Terminal */}
              <TerminalDemo />

              {/* Local System Telemetry Bento Card */}
              <Paper p="xl" withBorder style={{ backgroundColor: 'var(--color-slate-900)', borderColor: 'var(--color-slate-800)', height: '100%', minHeight: '420px', display: 'flex', flexDirection: 'column' }}>
                <Stack gap="md" style={{ flex: 1 }}>
                  <div>
                    <Title order={4} mb={4} style={{ fontFamily: 'Fira Sans', fontWeight: 700 }}>
                      System Engine Status
                    </Title>
                    <Text size="sm" c="dimmed">
                      Real-time stats from local caches & circuit breakers.
                    </Text>
                  </div>

                  <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                    <Paper p="md" withBorder style={{ backgroundColor: 'var(--color-slate-950)', borderColor: 'var(--color-slate-800)', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                      <Text size="xs" fw={600} c="dimmed" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Query Key Cache
                      </Text>
                      <Text size="xl" fw={800} c="var(--color-mint-500)" mt={4} style={{ fontFamily: 'Fira Code' }}>
                        {telemetry ? telemetry.total_cached_queries : '0'}
                      </Text>
                      <Text size="10px" c="dimmed" mt={4}>
                        query_cache table size
                      </Text>
                    </Paper>

                    <Paper p="md" withBorder style={{ backgroundColor: 'var(--color-slate-950)', borderColor: 'var(--color-slate-800)', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                      <Text size="xs" fw={600} c="dimmed" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Scraped Document Cache
                      </Text>
                      <Text size="xl" fw={800} c="var(--color-mint-500)" mt={4} style={{ fontFamily: 'Fira Code' }}>
                        {telemetry ? telemetry.total_scraped_pages : '0'}
                      </Text>
                      <Text size="10px" c="dimmed" mt={4}>
                        page_cache table size
                      </Text>
                    </Paper>

                    <Paper p="md" withBorder style={{ backgroundColor: 'var(--color-slate-950)', borderColor: 'var(--color-slate-800)', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                      <Text size="xs" fw={600} c="dimmed" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        HTTP Success Rate
                      </Text>
                      <Text size="xl" fw={800} c="var(--color-mint-500)" mt={4} style={{ fontFamily: 'Fira Code' }}>
                        {telemetry ? `${telemetry.scraper_success_rate}%` : '100.0%'}
                      </Text>
                      <Text size="10px" c="dimmed" mt={4}>
                        successful page fetches
                      </Text>
                    </Paper>

                    <Paper p="md" withBorder style={{ backgroundColor: 'var(--color-slate-950)', borderColor: 'var(--color-slate-800)', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                      <Text size="xs" fw={600} c="dimmed" style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Domain Breakers Open
                      </Text>
                      <Text size="xl" fw={800} c={telemetry && telemetry.active_circuit_breakers.length > 0 ? "red" : "var(--color-mint-500)"} mt={4} style={{ fontFamily: 'Fira Code' }}>
                        {telemetry ? telemetry.active_circuit_breakers.length : '0'}
                      </Text>
                      <Text size="10px" c="dimmed" mt={4}>
                        OPEN breakers (cooldown)
                      </Text>
                    </Paper>
                  </div>

                  {telemetry && telemetry.active_circuit_breakers.length > 0 && (
                    <Box p="xs" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: '6px' }}>
                      <Text size="xs" c="red" fw={600} mb={4}>
                        ⚠️ OPEN CIRCUITS:
                      </Text>
                      <Group gap={4}>
                        {telemetry.active_circuit_breakers.map((domain, index) => (
                          <Badge key={index} variant="filled" color="red" size="xs">
                            {domain}
                          </Badge>
                        ))}
                      </Group>
                    </Box>
                  )}
                </Stack>
              </Paper>
            </div>
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
          <GitNexusWebView />
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
