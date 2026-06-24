import { describe, it, expect } from 'vitest'
import { renderFunctionPlot } from '../lib/functionPlot'

describe('Function Plot', () => {
  it('renders function plot', () => {
    const div = document.createElement('div')
    // Should not throw
    expect(() => renderFunctionPlot(div, [{ fn: 'x^2' }])).not.toThrow()
  })
})
