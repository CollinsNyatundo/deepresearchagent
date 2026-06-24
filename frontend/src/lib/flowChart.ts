import { FlowNode, FlowEdge } from '../types/flow'

export interface FlowChartData {
  nodes: FlowNode[]
  edges: FlowEdge[]
}

export function createFlowChart(): FlowChartData {
  return {
    nodes: [
      { id: '1', type: 'input', position: { x: 0, y: 0 }, data: { label: 'Start' } },
      { id: '2', position: { x: 100, y: 100 }, data: { label: 'Process' } },
    ],
    edges: [
      { id: 'e1-2', source: '1', target: '2' },
    ],
  }
}
