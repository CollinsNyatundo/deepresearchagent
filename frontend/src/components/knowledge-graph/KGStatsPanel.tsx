/**
 * KGStatsPanel — Compact stats bar for the knowledge graph.
 *
 * Displays:
 * - Node count, edge count, community count
 * - Token compression ratio vs naive approach
 * - Top god nodes (highest connectivity)
 * - Top surprise connections with explanations
 */

import {
  Paper,
  Stack,
  Group,
  Text,
  Badge,
  Title,
  Divider,
  Tooltip,
  ThemeIcon,
  Progress,
  Anchor,
} from '@mantine/core';
import {
  IconNetwork,
  IconGitBranch,
  IconCrown,
  IconBolt,
  IconSparkles,
} from '@tabler/icons-react';
import type { KnowledgeGraph } from '../../types/api';

type KGStatsPanelProps = {
  kg: KnowledgeGraph;
  onGodNodeClick?: (nodeId: string) => void;
};

export function KGStatsPanel({ kg, onGodNodeClick }: KGStatsPanelProps) {
  const compressionPercent = kg.compression_ratio > 0
    ? Math.min(Math.round((1 - 1 / kg.compression_ratio) * 100), 99)
    : 0;

  return (
    <Stack gap="sm">
      {/* Node / Edge / Community counts */}
      <Paper p="sm" withBorder radius="md">
        <Title order={6} mb="sm" c="dimmed">
          Graph Statistics
        </Title>
        <Stack gap={6}>
          <Group justify="space-between">
            <Group gap="xs">
              <ThemeIcon size="xs" variant="light" color="indigo" radius="xl">
                <IconNetwork size={10} />
              </ThemeIcon>
              <Text size="xs" c="dimmed">Nodes</Text>
            </Group>
            <Badge variant="filled" color="indigo" size="sm">
              {kg.nodes.length.toLocaleString()}
            </Badge>
          </Group>

          <Group justify="space-between">
            <Group gap="xs">
              <ThemeIcon size="xs" variant="light" color="violet" radius="xl">
                <IconGitBranch size={10} />
              </ThemeIcon>
              <Text size="xs" c="dimmed">Edges</Text>
            </Group>
            <Badge variant="filled" color="violet" size="sm">
              {kg.edges.length.toLocaleString()}
            </Badge>
          </Group>

          <Group justify="space-between">
            <Group gap="xs">
              <ThemeIcon size="xs" variant="light" color="teal" radius="xl">
                <IconSparkles size={10} />
              </ThemeIcon>
              <Text size="xs" c="dimmed">Communities</Text>
            </Group>
            <Badge variant="filled" color="teal" size="sm">
              {kg.communities.length}
            </Badge>
          </Group>
        </Stack>
      </Paper>

      {/* Token compression */}
      {kg.compression_ratio > 1 && (
        <Paper p="sm" withBorder radius="md">
          <Group justify="space-between" mb={6}>
            <Group gap="xs">
              <ThemeIcon size="xs" variant="light" color="orange" radius="xl">
                <IconBolt size={10} />
              </ThemeIcon>
              <Text size="xs" c="dimmed">Token Efficiency</Text>
            </Group>
            <Tooltip
              label={`Graph queries use ~${kg.graph_token_cost.toLocaleString()} tokens vs ~${kg.naive_token_cost.toLocaleString()} for raw read`}
              withArrow
              multiline
              maw={240}
            >
              <Badge variant="light" color="orange" size="sm" style={{ cursor: 'help' }}>
                {kg.compression_ratio.toFixed(1)}× compression
              </Badge>
            </Tooltip>
          </Group>
          <Progress
            value={compressionPercent}
            color="orange"
            size="xs"
            radius="xl"
          />
          <Text size="xs" c="dimmed" mt={4}>
            {compressionPercent}% token savings vs reading raw files
          </Text>
        </Paper>
      )}

      {/* God nodes */}
      {kg.god_nodes.length > 0 && (
        <Paper p="sm" withBorder radius="md">
          <Title order={6} mb="xs" c="dimmed">
            <Group gap="xs">
              <IconCrown size={14} color="gold" />
              God Nodes
            </Group>
          </Title>
          <Stack gap={4}>
            {kg.god_nodes.slice(0, 7).map((nodeId) => {
              const node = kg.nodes.find((n) => n.id === nodeId);
              const label = node?.label || nodeId;
              return (
                <Group key={nodeId} justify="space-between">
                  <Anchor
                    size="xs"
                    onClick={() => onGodNodeClick?.(nodeId)}
                    style={{ cursor: 'pointer' }}
                  >
                    {label.length > 28 ? `${label.slice(0, 28)}…` : label}
                  </Anchor>
                  <Badge size="xs" variant="outline" color="gray">
                    {node?.degree ?? '?'} edges
                  </Badge>
                </Group>
              );
            })}
          </Stack>
        </Paper>
      )}

      {/* Surprise edges */}
      {kg.surprise_edges.length > 0 && (
        <Paper p="sm" withBorder radius="md">
          <Title order={6} mb="xs" c="dimmed">
            <Group gap="xs">
              <IconSparkles size={14} color="var(--mantine-color-violet-5)" />
              Surprise Connections
            </Group>
          </Title>
          <Stack gap={8}>
            {kg.surprise_edges.slice(0, 5).map((edge, i) => {
              const srcNode = kg.nodes.find((n) => n.id === edge.source);
              const tgtNode = kg.nodes.find((n) => n.id === edge.target);
              const srcLabel = srcNode?.label || edge.source;
              const tgtLabel = tgtNode?.label || edge.target;

              return (
                <div key={i}>
                  <Group gap={4} mb={2}>
                    <Badge size="xs" variant="dot" color="violet">
                      {(srcLabel.length > 16 ? `${srcLabel.slice(0, 16)}…` : srcLabel)}
                    </Badge>
                    <Text size="xs" c="dimmed">↔</Text>
                    <Badge size="xs" variant="dot" color="violet">
                      {(tgtLabel.length > 16 ? `${tgtLabel.slice(0, 16)}…` : tgtLabel)}
                    </Badge>
                  </Group>
                  <Text size="xs" c="dimmed" ml={4}>
                    {edge.reason.length > 80 ? `${edge.reason.slice(0, 80)}…` : edge.reason}
                  </Text>
                  {i < kg.surprise_edges.slice(0, 5).length - 1 && <Divider mt={6} />}
                </div>
              );
            })}
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}
