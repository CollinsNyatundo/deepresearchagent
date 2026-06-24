import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'

interface GraphNode extends d3.SimulationNodeDatum {
  id: string
  title: string
  degree: number
  community: number
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode
  target: string | GraphNode
}

interface NoteGraphData {
  id: string
  title: string
  outgoing_links: string[]
  backlink_count: number
}

interface NoteGraphProps {
  notes: NoteGraphData[]
  onNodeClick: (noteId: string) => void
  selectedNoteId: string | null
}

const AMBER_PALETTE = [
  '#c8956c', '#d4a574', '#b8845e', '#a07050', '#c0a080',
  '#d09060', '#b09070', '#c8a888', '#e0c0a0', '#9a7050',
]

export default function NoteGraph({ notes, onNodeClick, selectedNoteId }: NoteGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [stats, setStats] = useState({ nodes: 0, edges: 0 })

  useEffect(() => {
    if (!svgRef.current || notes.length === 0) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const container = svgRef.current.parentElement
    const width = container?.clientWidth || 800
    const height = container?.clientHeight || 600

    svg.attr('width', width).attr('height', height)

    // Build graph data
    const nodeMap = new Map<string, GraphNode>()
    const links: GraphLink[] = []

    notes.forEach(note => {
      const degree = note.outgoing_links.length + note.backlink_count
      nodeMap.set(note.id, {
        id: note.id,
        title: note.title || 'Untitled',
        degree,
        community: 0,
      })
    })

    // Extract links from outgoing wiki links
    notes.forEach(note => {
      note.outgoing_links.forEach(rawLink => {
        // Only handle plain note links for the graph
        if (!rawLink.includes(':')) {
          const targetNote = notes.find(n => n.title.toLowerCase() === rawLink.toLowerCase())
          if (targetNote && targetNote.id !== note.id) {
            links.push({ source: note.id, target: targetNote.id })
          }
        }
      })
    })

    // Community detection (simple: connected components)
    const communities: Map<string, number> = new Map()
    let communityId = 0
    const visited = new Set<string>()

    const bfs = (startId: string) => {
      const queue = [startId]
      visited.add(startId)
      communities.set(startId, communityId)
      while (queue.length > 0) {
        const curr = queue.shift()!
        links.forEach(l => {
          const s = typeof l.source === 'string' ? l.source : l.source.id
          const t = typeof l.target === 'string' ? l.target : l.target.id
          if (s === curr && !visited.has(t)) { visited.add(t); communities.set(t, communityId); queue.push(t) }
          if (t === curr && !visited.has(s)) { visited.add(s); communities.set(s, communityId); queue.push(s) }
        })
      }
    }

    nodeMap.forEach((_, id) => {
      if (!visited.has(id)) { bfs(id); communityId++ }
    })

    const nodes = Array.from(nodeMap.values()).map(n => ({
      ...n,
      community: communities.get(n.id) || 0,
    }))

    setStats({ nodes: nodes.length, edges: links.length })

    // Zoom group
    const g = svg.append('g')

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.15, 5])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
      })
    svg.call(zoom as any)

    // Simulation
    const simulation = d3.forceSimulation<GraphNode>(nodes)
      .force('link', d3.forceLink<GraphNode, GraphLink>(links).id(d => d.id).distance(120))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide<GraphNode>().radius(d => Math.sqrt(d.degree + 1) * 5.5 + 5))
      .force('x', d3.forceX(width / 2).strength(0.05))
      .force('y', d3.forceY(height / 2).strength(0.05))

    // Draw edges
    const link = g.append('g')
      .attr('stroke', 'rgba(200, 149, 108, 0.12)')
      .attr('stroke-opacity', 0.6)
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke-width', 1.5)

    // Draw nodes
    const node = g.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(d3.drag<SVGGElement, GraphNode>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event, d) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0)
          d.fx = null
          d.fy = null
        }) as any)

    node.append('circle')
      .attr('r', d => Math.sqrt(d.degree + 1) * 5.5)
      .attr('fill', d => AMBER_PALETTE[d.community % AMBER_PALETTE.length])
      .attr('stroke', '#1a1a1a')
      .attr('stroke-width', 1.5)
      .attr('opacity', 0.85)

    node.append('text')
      .text(d => d.title.length > 20 ? d.title.slice(0, 20) + '…' : d.title)
      .attr('x', 0)
      .attr('y', d => Math.sqrt(d.degree + 1) * 5.5 + 12)
      .attr('text-anchor', 'middle')
      .attr('fill', '#999')
      .attr('font-size', '10px')
      .attr('font-family', '-apple-system, sans-serif')
      .attr('pointer-events', 'none')

    // Hover effects
    node.on('mouseenter', function(_event, d) {
      const connectedIds = new Set<string>([d.id])
      links.forEach(l => {
        const s = typeof l.source === 'string' ? l.source : l.source.id
        const t = typeof l.target === 'string' ? l.target : l.target.id
        if (s === d.id) connectedIds.add(t)
        if (t === d.id) connectedIds.add(s)
      })

      node.style('opacity', n => connectedIds.has(n.id) ? 1 : 0.15)
      link.style('opacity', l => {
        const s = typeof l.source === 'string' ? l.source : l.source.id
        const t = typeof l.target === 'string' ? l.target : l.target.id
        return (s === d.id || t === d.id) ? 1 : 0.15
      })
      d3.select(this).select('circle').attr('stroke', '#c8956c').attr('stroke-width', 2.5)
    })

    node.on('mouseleave', function() {
      node.style('opacity', 1)
      link.style('opacity', 0.6)
      d3.select(this).select('circle').attr('stroke', '#1a1a1a').attr('stroke-width', 1.5)
    })

    node.on('click', (_event, d) => {
      onNodeClick(d.id)
    })

    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as GraphNode).x || 0)
        .attr('y1', d => (d.source as GraphNode).y || 0)
        .attr('x2', d => (d.target as GraphNode).x || 0)
        .attr('y2', d => (d.target as GraphNode).y || 0)

      node.attr('transform', d => `translate(${d.x || 0},${d.y || 0})`)
    })

    return () => {
      simulation.stop()
    }
  }, [notes, selectedNoteId])

  return (
    <div className="flex-1 relative flex flex-col">
      <div className="flex-1 relative">
        <svg
          ref={svgRef}
          className="w-full h-full"
          style={{ background: 'transparent', minHeight: '500px' }}
        />
      </div>
      <div className="absolute bottom-4 left-4 liquid-glass px-3 py-1.5 rounded-lg text-xs text-[#555]">
        {stats.nodes} nodes · {stats.edges} edges
      </div>
    </div>
  )
}
