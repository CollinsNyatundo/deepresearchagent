/**
 * GitNexusWebView — embeds the official GitNexus web UI (gitnexus.vercel.app)
 * inside an iframe and manages the local `gitnexus serve` bridge process.
 *
 * Architecture:
 *   1. User clicks "Start Local Server"
 *   2. We call POST /gitnexus/serve/start → backend spawns `npx gitnexus serve --port 4747`
 *   3. The iframe loads https://gitnexus.vercel.app which auto-detects localhost:4747
 *   4. GitNexus web UI connects and shows the full interactive codebase graph
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Stack,
  Group,
  Title,
  Text,
  Button,
  Badge,
  Alert,
  Paper,
  Loader,
  ThemeIcon,
  ActionIcon,
  Tooltip,
  Box,
  Code,
  Anchor,
} from '@mantine/core';
import {
  IconCode,
  IconPlayerPlay,
  IconPlayerStop,
  IconRefresh,
  IconExternalLink,
  IconAlertTriangle,
  IconCircleCheck,
  IconInfoCircle,
} from '@tabler/icons-react';
import { api } from '../../api/client';

interface ServeStatus {
  running: boolean;
  pid: number | null;
  port: number;
  web_ui_url: string;
}

const GITNEXUS_WEB_UI = 'https://gitnexus.vercel.app';
const POLL_INTERVAL_MS = 15_000; // 15s — serve status rarely changes

export function GitNexusWebView() {
  const [status, setStatus] = useState<ServeStatus | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState(0); // force iframe reload
  const [showIframe, setShowIframe] = useState(false);

  // ── Poll serve status ─────────────────────────────────────────────
  const fetchStatus = useCallback(async (silent = false) => {
    try {
      const s = await api.getGitnexusServeStatus();
      setStatus(s);
      if (s.running && !silent) setShowIframe(true);
    } catch {
      // silently swallow — server might just be starting up
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(() => fetchStatus(true), POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchStatus]);

  // ── Start / Stop ──────────────────────────────────────────────────
  const handleStart = async () => {
    setIsStarting(true);
    setError(null);
    try {
      await api.startGitnexusServe();
      await fetchStatus();
      setShowIframe(true);
      setIframeKey((k) => k + 1); // reload iframe after server comes up
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start gitnexus serve');
    } finally {
      setIsStarting(false);
    }
  };

  const handleStop = async () => {
    setIsStopping(true);
    setError(null);
    try {
      await api.stopGitnexusServe();
      await fetchStatus();
      setShowIframe(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop gitnexus serve');
    } finally {
      setIsStopping(false);
    }
  };

  const isRunning = status?.running ?? false;

  return (
    <Stack gap="md" style={{ height: '100%' }}>
      {/* ── Header controls ── */}
      <Paper
        p="md"
        radius="md"
        withBorder
        style={{
          background: 'linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(139,92,246,0.08) 100%)',
          borderColor: 'rgba(99,102,241,0.25)',
        }}
      >
        <Group justify="space-between" wrap="nowrap">
          <Group gap="sm">
            <ThemeIcon size={36} radius="md" variant="gradient" gradient={{ from: 'indigo', to: 'violet', deg: 135 }}>
              <IconCode size={20} />
            </ThemeIcon>
            <div>
              <Group gap="xs" mb={2}>
                <Text fw={600} size="sm">GitNexus Web UI</Text>
                {isRunning ? (
                  <Badge size="xs" color="teal" variant="filled" leftSection={<IconCircleCheck size={10} />}>
                    Server Running
                  </Badge>
                ) : (
                  <Badge size="xs" color="gray" variant="outline">
                    Server Stopped
                  </Badge>
                )}
                {isRunning && status?.pid && (
                  <Badge size="xs" color="indigo" variant="light">
                    PID {status.pid}
                  </Badge>
                )}
              </Group>
              <Text size="xs" c="dimmed">
                Powered by{' '}
                <Anchor href="https://gitnexus.vercel.app" target="_blank" size="xs" c="indigo">
                  gitnexus.vercel.app
                </Anchor>
                {' '}— interactive codebase topology, community detection &amp; process flows
              </Text>
            </div>
          </Group>

          <Group gap="xs">
            {isRunning && (
              <>
                <Tooltip label="Reload iframe">
                  <ActionIcon
                    variant="light"
                    color="indigo"
                    onClick={() => setIframeKey((k) => k + 1)}
                  >
                    <IconRefresh size={16} />
                  </ActionIcon>
                </Tooltip>
                <Tooltip label="Open in new tab">
                  <ActionIcon
                    variant="light"
                    color="violet"
                    component="a"
                    href={GITNEXUS_WEB_UI}
                    target="_blank"
                  >
                    <IconExternalLink size={16} />
                  </ActionIcon>
                </Tooltip>
              </>
            )}

            {!isRunning ? (
              <Button
                size="sm"
                variant="gradient"
                gradient={{ from: 'indigo', to: 'violet', deg: 135 }}
                leftSection={isStarting ? <Loader size="xs" color="white" /> : <IconPlayerPlay size={16} />}
                onClick={handleStart}
                loading={isStarting}
              >
                {isStarting ? 'Starting…' : 'Start Local Server'}
              </Button>
            ) : (
              <Button
                size="sm"
                variant="light"
                color="red"
                leftSection={isStopping ? <Loader size="xs" /> : <IconPlayerStop size={16} />}
                onClick={handleStop}
                loading={isStopping}
              >
                {isStopping ? 'Stopping…' : 'Stop Server'}
              </Button>
            )}
          </Group>
        </Group>

        {error && (
          <Alert
            icon={<IconAlertTriangle size={16} />}
            color="red"
            mt="sm"
            onClose={() => setError(null)}
            withCloseButton
          >
            {error}
          </Alert>
        )}
      </Paper>

      {/* ── Not running: instructional empty state ── */}
      {!isRunning && !isStarting && (
        <Stack align="center" justify="center" gap="xl" style={{ flex: 1, minHeight: 400 }}>
          <ThemeIcon size={80} radius="xl" variant="light" color="indigo">
            <IconCode size={48} />
          </ThemeIcon>
          <Stack align="center" gap="xs" maw={540}>
            <Title order={3}>GitNexus Web UI</Title>
            <Text c="dimmed" ta="center">
              Click <strong>Start Local Server</strong> above to launch{' '}
              <Code>npx gitnexus serve</Code> on port 4747. The official GitNexus
              web interface will auto-connect and display your full codebase graph —
              no configuration required.
            </Text>
          </Stack>

          <Paper p="md" radius="md" withBorder style={{ maxWidth: 480, width: '100%' }}>
            <Group gap="xs" mb="xs">
              <IconInfoCircle size={16} color="var(--mantine-color-indigo-6)" />
              <Text size="sm" fw={600}>What you'll see</Text>
            </Group>
            <Stack gap={6}>
              {[
                '🕸️  Interactive force-graph of every file, class & function',
                '🏘️  Auto-detected community clusters (functional modules)',
                '🔄  Execution flow traces end-to-end through your code',
                '🔍  Hybrid semantic + BM25 search across the entire codebase',
                '📄  Built-in code inspector with syntax highlighting',
              ].map((item) => (
                <Text key={item} size="sm" c="dimmed">{item}</Text>
              ))}
            </Stack>
          </Paper>

          <Group gap="md">
            <Button
              size="lg"
              variant="gradient"
              gradient={{ from: 'indigo', to: 'violet', deg: 135 }}
              leftSection={<IconPlayerPlay size={20} />}
              onClick={handleStart}
              loading={isStarting}
            >
              Start Local Server
            </Button>
            <Button
              size="lg"
              variant="light"
              color="gray"
              leftSection={<IconExternalLink size={20} />}
              component="a"
              href={GITNEXUS_WEB_UI}
              target="_blank"
            >
              Open Web UI Directly
            </Button>
          </Group>

          <Text size="xs" c="dimmed">
            Requires the GitNexus index (run{' '}
            <Code>npx gitnexus analyze</Code> first if you haven't already)
          </Text>
        </Stack>
      )}

      {/* ── Starting spinner ── */}
      {isStarting && (
        <Stack align="center" justify="center" gap="md" style={{ flex: 1, minHeight: 400 }}>
          <Loader size="xl" color="indigo" />
          <Text c="dimmed">Starting <Code>npx gitnexus serve</Code> on port 4747…</Text>
          <Text size="xs" c="dimmed">
            The GitNexus web UI will appear automatically once the server is ready.
          </Text>
        </Stack>
      )}

      {/* ── Iframe ── */}
      {isRunning && showIframe && (
        <Box
          style={{
            flex: 1,
            minHeight: 600,
            borderRadius: 12,
            overflow: 'hidden',
            border: '1px solid rgba(99,102,241,0.2)',
            boxShadow: '0 4px 24px rgba(99,102,241,0.12)',
          }}
        >
          <iframe
            key={iframeKey}
            src={GITNEXUS_WEB_UI}
            title="GitNexus Web UI"
            style={{
              width: '100%',
              height: '100%',
              minHeight: 600,
              border: 'none',
              display: 'block',
            }}
            allow="clipboard-write"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
          />
        </Box>
      )}

      {/* ── Running but iframe hidden (user manually toggled) ── */}
      {isRunning && !showIframe && (
        <Stack align="center" justify="center" gap="md" style={{ flex: 1, minHeight: 300 }}>
          <IconCircleCheck size={48} color="var(--mantine-color-teal-6)" />
          <Text fw={600}>Server is running on port 4747</Text>
          <Group gap="md">
            <Button variant="gradient" gradient={{ from: 'indigo', to: 'violet', deg: 135 }} onClick={() => setShowIframe(true)}>
              Show Web UI
            </Button>
            <Button
              variant="light"
              leftSection={<IconExternalLink size={16} />}
              component="a"
              href={GITNEXUS_WEB_UI}
              target="_blank"
            >
              Open in New Tab
            </Button>
          </Group>
        </Stack>
      )}
    </Stack>
  );
}
