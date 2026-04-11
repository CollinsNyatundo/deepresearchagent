import { useEffect, useState } from 'react';
import { Stack, NavLink, Text, Loader, ScrollArea, Badge, Group, Tooltip } from '@mantine/core';
import { IconFileText, IconClock, IconDownload } from '@tabler/icons-react';
import { api } from '../../api/client';
import type { RunSummary } from '../../types/api';

type Props = {
  selectedRunId: string | null;
  onSelectRun: (id: string) => void;
};

/** Map of run_id → whether any export is cached */
function useExportStatus(runs: RunSummary[]) {
  const [statusMap, setStatusMap] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (runs.length === 0) return;
    runs.forEach((run) => {
      api
        .listExports(run.id)
        .then(({ formats }) => {
          const hasCached = formats.some((f) => f.cached);
          setStatusMap((prev) => ({ ...prev, [run.id]: hasCached }));
        })
        .catch(() => {
          // Silently ignore — run may not be saved to disk yet
        });
    });
  }, [runs]);

  return statusMap;
}

export function RunList({ selectedRunId, onSelectRun }: Props) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .listRuns()
      .then(setRuns)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const exportStatus = useExportStatus(runs);

  if (loading) {
    return (
      <Stack align="center" justify="center" py="xl">
        <Loader size="sm" />
        <Text size="xs" c="dimmed">Loading runs…</Text>
      </Stack>
    );
  }

  if (error) {
    return (
      <Text c="red" size="sm" ta="center" py="md">
        Failed to load runs. Is the API server running?
      </Text>
    );
  }

  if (runs.length === 0) {
    return (
      <Stack align="center" py="xl" gap="xs">
        <IconFileText size={32} color="var(--mantine-color-gray-4)" />
        <Text c="dimmed" ta="center" size="sm">No research runs yet.</Text>
        <Text c="dimmed" ta="center" size="xs">Click "New Research" to get started.</Text>
      </Stack>
    );
  }

  return (
    <ScrollArea style={{ flex: 1 }} offsetScrollbars>
      <Stack gap={4}>
        {runs.map((run) => (
          <NavLink
            key={run.id}
            active={run.id === selectedRunId}
            label={
              <Text size="sm" lineClamp={2} fw={run.id === selectedRunId ? 600 : 400}>
                {run.query}
              </Text>
            }
            description={
              <Group gap={4} mt={2}>
                <IconClock size={12} />
                <Text size="xs">{formatDate(run.created_at)}</Text>
              </Group>
            }
            leftSection={<IconFileText size={18} />}
            rightSection={
              <Group gap={4} wrap="nowrap">
                {exportStatus[run.id] && (
                  <Tooltip label="Exports available" withArrow position="right">
                    <Badge
                      size="xs"
                      variant="light"
                      color="teal"
                      leftSection={<IconDownload size={10} />}
                    >
                      DL
                    </Badge>
                  </Tooltip>
                )}
                {run.model_used && (
                  <Badge size="xs" variant="light" color="gray">
                    {run.model_used.split('/').pop()?.replace(/:.*$/, '').slice(0, 12) || ''}
                  </Badge>
                )}
              </Group>
            }
            onClick={() => onSelectRun(run.id)}
            style={{ borderRadius: 'var(--mantine-radius-md)' }}
          />
        ))}
      </Stack>
    </ScrollArea>
  );
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch {
    return dateStr;
  }
}
