import { useEffect, useState, useCallback } from 'react';
import { Map, Download } from 'lucide-react';
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
      <div className="flex justify-center items-center py-[100px]">
        <div className="flex flex-col items-center gap-1">
          <div className="w-8 h-8 border-2 border-[#c8956c] border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-[#999]">Loading mindmap…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center py-[100px]">
        <p className="text-sm text-[#c45a5a]">{error}</p>
      </div>
    );
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="flex justify-center items-center py-[100px]">
        <div className="flex flex-col items-center gap-1">
          <Map size={48} className="text-[#555]" />
          <p className="text-[#999]">No mindmap data available for this run.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-0 h-[calc(100vh-200px)]">
      {/* Export header */}
      <div className="flex justify-end items-center px-4 py-1">
        <button
          title="Download mindmap as G6-compatible JSON"
          className="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-xl bg-[#c8956c]/15 hover:bg-[#c8956c]/25 text-[#c8956c] transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={exportingJson}
          onClick={handleExportJson}
        >
          {exportingJson ? (
            <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Download size={14} />
          )}
          Export JSON
        </button>
      </div>

      {/* Graph + details panel */}
      <div className="flex items-start flex-nowrap gap-0 flex-1 min-h-0">
        <div className="flex-1 h-full">
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
      </div>
    </div>
  );
}
