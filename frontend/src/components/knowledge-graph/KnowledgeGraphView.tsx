/**
 * KnowledgeGraphView — Force-directed knowledge graph visualization.
 *
 * Uses AntV G6 (already installed) with force layout to render the
 * Graphify knowledge graph. Key features:
 *
 * - Nodes: sized by degree, colored by community, gold ring on god nodes
 * - Edges: solid = EXTRACTED, dashed = INFERRED, dotted = AMBIGUOUS
 * - Sidebar: community legend, god node list, surprise connections
 * - Zoom/pan controls, community filter toggles
 * - "Open Interactive HTML" button → opens graph.html in new tab
 * - Node click → detail popover with summary, provenance, confidence
 * - Strategy D: this replaces the tree mindmap for runs with KG data
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import {
  Stack,
  Group,
  Button,
  Loader,
  Text,
  Title,
  Badge,
  Tabs,
  Alert,
  ActionIcon,
  Tooltip,
  ScrollArea,
  Popover,
  Divider,
  ThemeIcon,
  Progress,
} from '@mantine/core';
import {
  IconExternalLink,
  IconRefresh,
  IconZoomIn,
  IconZoomOut,
  IconFocus,
  IconAlertTriangle,
  IconCrown,
  IconNetwork,
  IconSearch,
} from '@tabler/icons-react';
import { api } from '../../api/client';
import type { KnowledgeGraph, KGNode } from '../../types/api';
import { CommunityLegend, getCommunityColor } from './CommunityLegend';
import { KGStatsPanel } from './KGStatsPanel';
import { KGQueryPanel } from './KGQueryPanel';

type KnowledgeGraphViewProps = {
  runId: string;
};

// Node size scale by degree
function getNodeSize(degree: number): number {
  if (degree > 20) return 38;
  if (degree > 10) return 28;
  if (degree > 5) return 22;
  if (degree > 2) return 18;
  return 14;
}

// Edge dash style by provenance
function getEdgeStyle(provenance: string) {
  switch (provenance) {
    case 'INFERRED':
      return { lineDash: [6, 4] };
    case 'AMBIGUOUS':
      return { lineDash: [2, 4] };
    default:
      return { lineDash: [0, 0] };
  }
}

// Edge color by type
function getEdgeColor(type: string): string {
  const typeColors: Record<string, string> = {
    calls: '#4F46E5',
    imports: '#059669',
    rationale_for: '#D97706',
    semantically_similar_to: '#6B7280',
    has_step: '#7C3AED',
    references: '#0891B2',
  };
  return typeColors[type] || '#6B7280';
}

export function KnowledgeGraphView({ runId }: KnowledgeGraphViewProps) {
  const graphRef = useRef<HTMLDivElement>(null);
  const g6Instance = useRef<any>(null);

  const [kg, setKg] = useState<KnowledgeGraph | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isBuilding, setIsBuilding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notBuilt, setNotBuilt] = useState(false);

  const [hiddenCommunities, setHiddenCommunities] = useState<Set<number>>(new Set());
  const [selectedNode, setSelectedNode] = useState<KGNode | null>(null);
  const [popoverOpened, setPopoverOpened] = useState(false);
  const [activeTab, setActiveTab] = useState<string | null>('graph');

  // ── Load knowledge graph ────────────────────────────────────────
  const loadKg = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setNotBuilt(false);
    try {
      const data = await api.getKnowledgeGraph(runId);
      setKg(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load knowledge graph';
      if (msg.includes('404') || msg.includes('not built')) {
        setNotBuilt(true);
      } else {
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    loadKg();
  }, [loadKg]);

  // ── Build KG manually ──────────────────────────────────────────
  const handleBuild = async () => {
    setIsBuilding(true);
    setError(null);
    try {
      const built = await api.buildKnowledgeGraph(runId);
      setKg(built);
      setNotBuilt(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Build failed');
    } finally {
      setIsBuilding(false);
    }
  };

  // ── Render G6 graph ─────────────────────────────────────────────
  useEffect(() => {
    if (!kg || !graphRef.current || activeTab !== 'graph') return;

    // Cleanup previous instance
    if (g6Instance.current) {
      try {
        g6Instance.current.destroy();
      } catch {}
      g6Instance.current = null;
    }

    const container = graphRef.current;
    const width = container.offsetWidth || 800;
    const height = container.offsetHeight || 600;

    // Dynamically import G6 to avoid SSR issues
    import('@antv/g6').then(({ Graph }) => {
      // Filter nodes by visible communities
      const visibleNodes = kg.nodes.filter(
        (n) => !hiddenCommunities.has(n.community)
      );
      const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));
      const visibleEdges = kg.edges.filter(
        (e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
      );

      // Transform to G6 data format
      const graphData = {
        nodes: visibleNodes.map((node) => ({
          id: node.id,
          // G6 v5 label
          label: node.label.length > 20
            ? node.label.slice(0, 20) + '…'
            : node.label,
          style: {
            size: getNodeSize(node.degree),
            fill: getCommunityColor(node.community),
            stroke: node.is_god_node ? '#FFD700' : '#1e293b',
            lineWidth: node.is_god_node ? 3 : 1,
            fillOpacity: node.provenance === 'AMBIGUOUS' ? 0.5 : 1,
          },
          data: node,  // stored for click handler
        })),
        edges: visibleEdges.map((edge, i) => ({
          id: `edge-${i}`,
          source: edge.source,
          target: edge.target,
          label: edge.label || edge.type,
          style: {
            stroke: getEdgeColor(edge.type),
            lineWidth: Math.max(1, edge.confidence * 2),
            opacity: 0.6,
            ...getEdgeStyle(edge.provenance),
          },
          data: edge,
        })),
      };

      const graph = new Graph({
        container,
        width,
        height,
        data: graphData,
        layout: {
          type: 'force',
          preventOverlap: true,
          nodeSize: 30,
          linkDistance: 120,
          nodeStrength: -80,
          edgeStrength: 0.4,
          iterations: 300,
        },
        node: {
          type: 'circle',
          style: {
            labelPlacement: 'bottom',
            labelFontSize: 10,
            labelFill: '#e2e8f0',
            labelMaxWidth: 80,
          },
        },
        edge: {
          type: 'line',
          style: {
            labelFontSize: 9,
            labelFill: '#94a3b8',
            endArrow: true,
          },
        },
        behaviors: ['zoom-canvas', 'drag-canvas', 'drag-node'],
        autoFit: 'view',
        animation: false,
        theme: 'dark',
      });

      // Node click → show detail popover
      graph.on('node:click', (evt: any) => {
        const nodeData = evt.target?.getModel?.()?.data || evt.itemType === 'node' ? evt.target : null;
        if (nodeData) {
          const originalNode = kg.nodes.find((n) => n.id === (nodeData.id || nodeData.data?.id));
          if (originalNode) {
            setSelectedNode(originalNode);
            setPopoverOpened(true);
          }
        }
      });

      graph.render();
      g6Instance.current = graph;
    }).catch((err) => {
      console.warn('G6 import failed:', err);
    });

    return () => {
      if (g6Instance.current) {
        try { g6Instance.current.destroy(); } catch {}
        g6Instance.current = null;
      }
    };
  }, [kg, hiddenCommunities, activeTab]);

  // ── Toggle community visibility ─────────────────────────────────
  const handleToggleCommunity = useCallback((id: number) => {
    setHiddenCommunities((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // ── Zoom controls ───────────────────────────────────────────────
  const handleZoomIn = () => g6Instance.current?.zoom(1.2);
  const handleZoomOut = () => g6Instance.current?.zoom(0.8);
  const handleFit = () => g6Instance.current?.fitView(20);

  // ── Focus on god node ───────────────────────────────────────────
  const handleGodNodeClick = useCallback((nodeId: string) => {
    if (!g6Instance.current) return;
    try {
      const item = g6Instance.current.findById?.(nodeId);
      if (item) {
        g6Instance.current.focusItem(item);
        g6Instance.current.setItemState(item, 'selected', true);
      }
    } catch {}
    setActiveTab('graph');
  }, []);

  // ─────────────────────────────────────────────────────────────────
  // Render states
  // ─────────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <Stack align="center" justify="center" style={{ height: '60vh' }}>
        <Loader size="xl" color="indigo" />
        <Title order={4} c="dimmed">Loading Knowledge Graph...</Title>
        <Text c="dimmed" size="sm">
          This may take a moment for large graphs.
        </Text>
      </Stack>
    );
  }

  if (notBuilt) {
    return (
      <Stack align="center" justify="center" style={{ height: '60vh' }} gap="xl">
        <ThemeIcon size={80} variant="light" color="indigo" radius="xl">
          <IconNetwork size={48} />
        </ThemeIcon>
        <div style={{ textAlign: 'center' }}>
          <Title order={3} mb="xs">Knowledge Graph Not Built</Title>
          <Text c="dimmed" maw={500}>
            The knowledge graph for this run hasn't been built yet.
            Building converts the research findings into a structured, navigable graph
            with automatic community detection and cross-domain relationship discovery.
          </Text>
        </div>
        <Button
          size="lg"
          variant="gradient"
          gradient={{ from: 'indigo', to: 'violet', deg: 135 }}
          leftSection={isBuilding ? <Loader size="xs" color="white" /> : <IconNetwork size={20} />}
          onClick={handleBuild}
          loading={isBuilding}
        >
          {isBuilding ? 'Building Knowledge Graph...' : 'Build Knowledge Graph'}
        </Button>
        {isBuilding && (
          <Stack align="center" gap="xs">
            <Text size="sm" c="dimmed">
              Exporting corpus → Running Graphify → Parsing graph...
            </Text>
            <Progress size="sm" value={100} animated color="indigo" w={300} />
          </Stack>
        )}
        {error && (
          <Alert icon={<IconAlertTriangle size={16} />} color="red" title="Build Failed" maw={500}>
            {error}
          </Alert>
        )}
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert icon={<IconAlertTriangle size={16} />} color="red" title="Error" m="md">
        {error}
        <Button mt="xs" size="xs" variant="light" onClick={loadKg}>Retry</Button>
      </Alert>
    );
  }

  if (!kg) return null;

  const visibleNodes = kg.nodes.filter((n) => !hiddenCommunities.has(n.community));

  return (
    <Group align="flex-start" gap="md" style={{ height: 'calc(100vh - 140px)' }}>
      {/* ── Left Sidebar ── */}
      <ScrollArea
        style={{ width: 240, flexShrink: 0, height: '100%' }}
        type="scroll"
      >
        <Stack gap="sm" pb="xl">
          {/* Action buttons */}
          <Group gap="xs">
            {kg.graph_html_available && (
              <Tooltip label="Open interactive graph.html in new tab" withArrow>
                <Button
                  size="xs"
                  variant="light"
                  color="teal"
                  leftSection={<IconExternalLink size={12} />}
                  onClick={() => window.open(api.getGraphHtmlUrl(runId), '_blank')}
                  fullWidth
                >
                  Open Interactive
                </Button>
              </Tooltip>
            )}
            <Tooltip label="Rebuild knowledge graph" withArrow>
              <ActionIcon
                size="sm"
                variant="subtle"
                color="gray"
                onClick={() => { setNotBuilt(true); }}
              >
                <IconRefresh size={14} />
              </ActionIcon>
            </Tooltip>
          </Group>

          <KGStatsPanel kg={kg} onGodNodeClick={handleGodNodeClick} />
          <CommunityLegend
            communities={kg.communities}
            hiddenCommunities={hiddenCommunities}
            onToggleCommunity={handleToggleCommunity}
          />

          {/* Visible node count info */}
          {hiddenCommunities.size > 0 && (
            <Text size="xs" c="dimmed" ta="center">
              {visibleNodes.length} / {kg.nodes.length} nodes visible
            </Text>
          )}
        </Stack>
      </ScrollArea>

      {/* ── Main Content ── */}
      <Stack style={{ flex: 1, height: '100%' }} gap="xs">
        {/* Tab bar */}
        <Tabs value={activeTab} onChange={setActiveTab} variant="pills">
          <Group justify="space-between">
            <Tabs.List>
              <Tabs.Tab value="graph" leftSection={<IconNetwork size={14} />}>
                Graph
              </Tabs.Tab>
              <Tabs.Tab value="query" leftSection={<IconSearch size={14} />}>
                Query
              </Tabs.Tab>
            </Tabs.List>

            {/* Zoom controls (only in graph tab) */}
            {activeTab === 'graph' && (
              <Group gap="xs">
                <Tooltip label="Zoom in" withArrow>
                  <ActionIcon size="sm" variant="subtle" onClick={handleZoomIn}>
                    <IconZoomIn size={14} />
                  </ActionIcon>
                </Tooltip>
                <Tooltip label="Zoom out" withArrow>
                  <ActionIcon size="sm" variant="subtle" onClick={handleZoomOut}>
                    <IconZoomOut size={14} />
                  </ActionIcon>
                </Tooltip>
                <Tooltip label="Fit to view" withArrow>
                  <ActionIcon size="sm" variant="subtle" onClick={handleFit}>
                    <IconFocus size={14} />
                  </ActionIcon>
                </Tooltip>

                {/* Edge legend */}
                <Group gap="xs" ml="sm">
                  <Text size="xs" c="dimmed">Edges:</Text>
                  <Badge size="xs" variant="outline" color="gray">━━ Extracted</Badge>
                  <Badge size="xs" variant="outline" color="indigo">╌╌ Inferred</Badge>
                  <Badge size="xs" variant="outline" color="violet">··· Ambiguous</Badge>
                </Group>
              </Group>
            )}
          </Group>

          {/* Graph panel */}
          <Tabs.Panel value="graph" style={{ height: 'calc(100% - 40px)' }}>
            <div
              ref={graphRef}
              style={{
                width: '100%',
                height: '100%',
                minHeight: 500,
                background: '#0f172a',
                borderRadius: 8,
                border: '1px solid #1e293b',
                position: 'relative',
              }}
            />

            {/* Node detail popover */}
            <Popover
              opened={popoverOpened}
              onClose={() => setPopoverOpened(false)}
              position="right"
              withArrow
            >
              <Popover.Target>
                <div style={{ position: 'absolute', top: 50, right: 16 }} />
              </Popover.Target>
              <Popover.Dropdown maw={320}>
                {selectedNode && (
                  <Stack gap="xs" p="xs">
                    <Group justify="space-between">
                      <Group gap="xs">
                        {selectedNode.is_god_node && (
                          <IconCrown size={16} color="gold" />
                        )}
                        <Text fw={600} size="sm">{selectedNode.label}</Text>
                      </Group>
                      <Badge size="xs" variant="light" color="indigo">
                        {selectedNode.type}
                      </Badge>
                    </Group>

                    <Group gap="xs">
                      <Badge size="xs" variant="dot"
                        color={selectedNode.provenance === 'EXTRACTED' ? 'teal'
                          : selectedNode.provenance === 'INFERRED' ? 'orange'
                          : 'red'}>
                        {selectedNode.provenance}
                      </Badge>
                      <Badge size="xs" variant="outline" color="gray">
                        {selectedNode.degree} edges
                      </Badge>
                      <Badge size="xs" variant="outline" color="gray">
                        Community {selectedNode.community}
                      </Badge>
                    </Group>

                    {selectedNode.confidence < 1 && (
                      <Group gap="xs">
                        <Text size="xs" c="dimmed">Confidence:</Text>
                        <Progress
                          value={selectedNode.confidence * 100}
                          color={selectedNode.confidence > 0.7 ? 'teal' : 'orange'}
                          size="xs"
                          style={{ flex: 1 }}
                        />
                        <Text size="xs" c="dimmed">
                          {(selectedNode.confidence * 100).toFixed(0)}%
                        </Text>
                      </Group>
                    )}

                    {selectedNode.summary && (
                      <>
                        <Divider />
                        <Text size="xs" c="dimmed" style={{ lineHeight: 1.5 }}>
                          {selectedNode.summary.length > 200
                            ? selectedNode.summary.slice(0, 200) + '…'
                            : selectedNode.summary}
                        </Text>
                      </>
                    )}

                    {selectedNode.file_path && (
                      <Text size="xs" c="dimmed" ff="monospace">
                        {selectedNode.file_path}
                      </Text>
                    )}
                  </Stack>
                )}
              </Popover.Dropdown>
            </Popover>
          </Tabs.Panel>

          {/* Query panel */}
          <Tabs.Panel value="query" pt="sm">
            <KGQueryPanel runId={runId} />
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Group>
  );
}
