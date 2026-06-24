import { describe, it, expect } from 'vitest'
import { createFlowChart } from '../lib/flowChart'

describe('Flow Chart', () => {
  it('creates default flow chart', () => {
    const chart = createFlowChart()
    expect(chart.nodes).toHaveLength(2)
    expect(chart.edges).toHaveLength(1)
  })
})
