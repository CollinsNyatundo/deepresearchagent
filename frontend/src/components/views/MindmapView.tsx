import { useEffect, useState, useCallback } from 'react';
import { Group, Loader, Center, Text, Stack, Button, Tooltip } from '@mantine/core';
import { IconMapOff, IconDownload } from '@tabler/icons-react';
import { G6MindmapGraph } from '../mindmap/G6MindmapGraph';
import { NodeDetailsPanel } from '../mindmap/NodeDetailsPanel';
import { api } from '../../api/client';
import type { MindmapGraph, MindmapNode } from '../../types/api';

type Props = {
  runId: string;
};

export function MindmapView({ runId }: Props) {
  const [graphData, setGraphData] = useState<MindmapGraph | null>(null);
  const [selectedNode, setSelectedNode] = useState<MindmapNode | null>(null);
  const [isExpanding, setIsExpanding] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exportingJson, setExportingJson] = useState(false);

  const handleExportJson = useCallback(async () => {
    setExportingJson(true);
    try {
      const blob = await api.exportRun(runId, 'mindmap_json');
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mindmap_${runId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Mindmap export failed:', err);
    } finally {
      setExportingJson(false);
    }
  }, [runId]);

  // Fetch mindmap data when run changes
  useEffect(() => {
    setLoading(true);
    setError(null);
    setSelectedNode(null);
    api
      .getMindmap(runId)
      .then(setGraphData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [runId]);

  // Handle node selection
  const handleNodeSelect = useCallback(
    (nodeId: string) => {
      if (!graphData) return;
      const node = graphData.nodes.find((n) => n.id === nodeId);
      if (node) setSelectedNode(node);
    },
    [graphData],
  );

  // Handle drill-deeper expansion
  const handleDrillDeeper = useCallback(
    async (nodeId: string) => {
      if (!graphData) return;
      setIsExpanding(true);
      try {
        const expansion = await api.expandNode(runId, nodeId);
        if (expansion.new_nodes.length > 0) {
          setGraphData((prev) => {
            if (!prev) return prev;
            return {
              ...prev,
              nodes: [...prev.nodes, ...expansion.new_nodes],
              edges: [...prev.edges, ...expansion.new_edges],
            };
          });
        }
      } catch (err) {
        console.error('Expansion failed:', err);
      } finally {
        setIsExpanding(false);
      }
    },
    [graphData, runId],
  );

  if (loading) {
    return (
      <Center py={100}>
        <Stack align="center" gap="xs">
          <Loader size="lg" />
          <Text size="sm" c="dimmed">Loading mindmap…</Text>
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

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <Center py={100}>
        <Stack align="center" gap="xs">
          <IconMapOff size={48} color="var(--mantine-color-gray-4)" />
          <Text c="dimmed">No mindmap data available for this run.</Text>
        </Stack>
      </Center>
    );
  }

  return (
    <Stack gap={0} style={{ height: 'calc(100vh - 200px)' }}>
      {/* Export header */}
      <Group justify="flex-end" px="md" py="xs">
        <Tooltip label="Download mindmap as G6-compatible JSON" withArrow>
          <Button
            size="xs"
            variant="light"
            color="violet"
            leftSection={<IconDownload size={14} />}
            loading={exportingJson}
            onClick={handleExportJson}
          >
            Export JSON
          </Button>
        </Tooltip>
      </Group>

      {/* Graph + details panel */}
      <Group
        align="flex-start"
        gap={0}
        wrap="nowrap"
        style={{ flex: 1, minHeight: 0 }}
      >
        <div style={{ flex: 1, height: '100%' }}>
          <G6MindmapGraph
            graphData={graphData}
            selectedNodeId={selectedNode?.id}
            onNodeSelect={handleNodeSelect}
          />
        </div>
        {selectedNode && (
          <NodeDetailsPanel
            node={selectedNode}
            onDrillDeeper={handleDrillDeeper}
            loading={isExpanding}
          />
        )}
      </Group>
    </Stack>
  );
}
