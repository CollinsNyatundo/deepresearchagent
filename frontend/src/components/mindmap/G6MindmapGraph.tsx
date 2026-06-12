import { useEffect, useRef, useCallback } from 'react';
import { Box } from '@mantine/core';
import { Graph } from '@antv/g6';
import type { MindmapGraph as MindmapData } from '../../types/api';

// ─── Node visual styles by type ─────────────────────────────────────

const NODE_STYLES = {
  root: {
    fill: '#4f46e5',
    stroke: '#3730a3',
    labelFill: '#ffffff',
    width: 220,
    height: 48,
    fontSize: 15,
    fontWeight: 700,
  },
  section: {
    fill: '#ecfdf5',
    stroke: '#059669',
    labelFill: '#064e3b',
    width: 180,
    height: 40,
    fontSize: 13,
    fontWeight: 500,
  },
  detail: {
    fill: '#f0f9ff',
    stroke: '#0284c7',
    labelFill: '#0c4a6e',
    width: 150,
    height: 36,
    fontSize: 12,
    fontWeight: 400,
  },
} as const;

const SELECTED_FILL = '#fbbf24';

// ─── Props ──────────────────────────────────────────────────────────

type Props = {
  graphData: MindmapData | null;
  selectedNodeId?: string;
  onNodeSelect?: (nodeId: string) => void;
};

// ─── Component ──────────────────────────────────────────────────────

export function G6MindmapGraph({ graphData, selectedNodeId, onNodeSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);

  /**
   * Convert our API MindmapGraph → G6 data format.
   */
  const toG6Data = useCallback(
    (data: MindmapData) => ({
      nodes: data.nodes.map((n) => {
        const style = NODE_STYLES[n.type] || NODE_STYLES.detail;
        const isSelected = n.id === selectedNodeId;
        return {
          id: n.id,
          data: { ...n },
          style: {
            fill: isSelected ? SELECTED_FILL : style.fill,
            stroke: isSelected ? '#d97706' : style.stroke,
            lineWidth: isSelected ? 3 : 1.5,
            radius: 8,
            labelText: n.label.length > 35 ? n.label.slice(0, 34) + '…' : n.label,
            labelFill: isSelected ? '#78350f' : style.labelFill,
            labelFontSize: style.fontSize,
            labelFontWeight: style.fontWeight,
            labelFontFamily: 'Inter, system-ui, sans-serif',
            labelMaxWidth: style.width - 20,
            labelWordWrap: true,
            size: [style.width, style.height] as [number, number],
          },
        };
      }),
      edges: data.edges.map((e, i) => ({
        id: `edge-${i}`,
        source: e.source,
        target: e.target,
        style: {
          stroke: '#c4c9d4',
          lineWidth: 1.5,
          endArrow: false,
        },
      })),
    }),
    [selectedNodeId],
  );

  // Initialize graph on mount / data change
  useEffect(() => {
    if (!containerRef.current || !graphData || graphData.nodes.length === 0) return;

    // Destroy previous instance
    if (graphRef.current) {
      try { graphRef.current.destroy(); } catch { /* noop */ }
      graphRef.current = null;
    }

    const graph = new Graph({
      container: containerRef.current,
      autoFit: 'view',
      padding: [40, 60, 40, 60],
      data: toG6Data(graphData),
      layout: {
        type: 'mindmap',
        direction: 'H',
        getHeight: () => 40,
        getWidth: (d: any) => {
          const nodeType = d?.data?.type || d?.type;
          return NODE_STYLES[nodeType as keyof typeof NODE_STYLES]?.width || 150;
        },
        getVGap: () => 20,
        getHGap: () => 60,
      },
      node: {
        style: {
          radius: 8,
        },
      },
      edge: {
        type: 'cubic-horizontal',
        style: {
          stroke: '#c4c9d4',
          lineWidth: 1.5,
        },
      },
      behaviors: ['drag-canvas', 'zoom-canvas'],
      animation: false,
    });

    // Click handler
    graph.on('node:click', (e: any) => {
      const nodeId = e.target?.id || e.itemId;
      if (nodeId && onNodeSelect) {
        onNodeSelect(nodeId);
      }
    });

    graph.render();
    graphRef.current = graph;

    // Set up ResizeObserver for responsive canvas scaling
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (graphRef.current && width > 0 && height > 0) {
          try {
            graphRef.current.setSize(width, height);
          } catch (err) {
            console.error("G6 resize error:", err);
          }
        }
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      try { graph.destroy(); } catch { /* noop */ }
      graphRef.current = null;
    };
    // Intentionally not including toG6Data to avoid re-init on selection change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphData, onNodeSelect]);

  // Update styling when selection changes (without full re-init)
  useEffect(() => {
    if (!graphRef.current || !graphData) return;
    try {
      graphRef.current.setData(toG6Data(graphData));
      graphRef.current.draw();
    } catch {
      // Graph may not be ready yet
    }
  }, [selectedNodeId, graphData, toG6Data]);

  // Listen to citation highlight events
  useEffect(() => {
    const handleHighlight = (e: Event) => {
      const customEvent = e as CustomEvent<{ url: string; id: string }>;
      const { id } = customEvent.detail;
      if (!graphRef.current || !graphData || !id) return;

      try {
        const nodesToHighlight: string[] = [];
        graphData.nodes.forEach((n) => {
          const matchesId = n.citations?.includes(id) || n.citations?.includes(id.replace(/^c/, ''));
          if (matchesId) {
            nodesToHighlight.push(n.id);
          }
        });

        if (nodesToHighlight.length > 0) {
          const updatedNodes = graphData.nodes.map((n) => {
            const style = NODE_STYLES[n.type] || NODE_STYLES.detail;
            const isHighlighted = nodesToHighlight.includes(n.id);
            const isSelected = n.id === selectedNodeId;
            return {
              id: n.id,
              data: { ...n },
              style: {
                fill: isSelected ? SELECTED_FILL : (isHighlighted ? '#fbbf24' : style.fill),
                stroke: isSelected ? '#d97706' : (isHighlighted ? '#fbbf24' : style.stroke),
                lineWidth: isSelected || isHighlighted ? 3 : 1.5,
                radius: 8,
                labelText: n.label.length > 35 ? n.label.slice(0, 34) + '…' : n.label,
                labelFill: isSelected ? '#78350f' : style.labelFill,
                labelFontSize: style.fontSize,
                labelFontWeight: style.fontWeight,
                labelFontFamily: 'Inter, system-ui, sans-serif',
                labelMaxWidth: style.width - 20,
                labelWordWrap: true,
                size: [style.width, style.height] as [number, number],
              },
            };
          });
          
          graphRef.current.setData({
            nodes: updatedNodes,
            edges: graphData.edges.map((e, i) => ({
              id: `edge-${i}`,
              source: e.source,
              target: e.target,
              style: {
                stroke: '#c4c9d4',
                lineWidth: 1.5,
                endArrow: false,
              },
            })),
          });
          graphRef.current.draw();
        }
      } catch (err) {
        console.error("Failed to highlight citation nodes:", err);
      }
    };

    const handleClearHighlight = () => {
      if (!graphRef.current || !graphData) return;
      try {
        graphRef.current.setData(toG6Data(graphData));
        graphRef.current.draw();
      } catch (err) {
        console.error("Failed to clear highlight:", err);
      }
    };

    window.addEventListener('highlight-citation', handleHighlight);
    window.addEventListener('clear-highlight-citation', handleClearHighlight);

    return () => {
      window.removeEventListener('highlight-citation', handleHighlight);
      window.removeEventListener('clear-highlight-citation', handleClearHighlight);
    };
  }, [graphData, selectedNodeId, toG6Data]);

  return (
    <Box
      ref={containerRef}
      style={{
        width: '100%',
        height: 'calc(100vh - 200px)',
        minHeight: 500,
        border: '1px solid var(--mantine-color-gray-3)',
        borderRadius: 'var(--mantine-radius-md)',
        background: 'linear-gradient(135deg, #fafbfc 0%, #f0f4ff 100%)',
        overflow: 'hidden',
      }}
    />
  );
}
