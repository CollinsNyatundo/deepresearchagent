export interface FlowNode {
  id: string
  type?: string
  position: { x: number; y: number }
  data: { label: string }
}

export interface FlowEdge {
  id: string
  source: string
  target: string
  type?: string
}
