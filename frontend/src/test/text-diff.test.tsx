import { describe, it, expect } from 'vitest'
import { computeDiff, renderDiffToHtml } from '../lib/textDiff'

describe('Text Diff', () => {
  it('computes diff between two texts', () => {
    const oldText = 'Hello World\nThis is old'
    const newText = 'Hello World\nThis is new'
    
    const result = computeDiff(oldText, newText)
    
    expect(result.unified).toContain('--- old')
    expect(result.unified).toContain('+++ new')
    expect(result.added).toBe(1)
    expect(result.removed).toBe(1)
  })

  it('renders diff to HTML', () => {
    const oldText = 'line1\nline2'
    const newText = 'line1\nline3'
    
    const diff = computeDiff(oldText, newText)
    const html = renderDiffToHtml(diff)
    
    expect(html).toContain('diff-add')
    expect(html).toContain('diff-remove')
    expect(html).toContain('diff-context')
  })

  it('counts unchanged lines correctly', () => {
    const oldText = 'unchanged\nremoved'
    const newText = 'unchanged\nadded'
    
    const result = computeDiff(oldText, newText)
    
    expect(result.unchanged).toBeGreaterThan(0)
    expect(result.added).toBe(1)
    expect(result.removed).toBe(1)
  })
})
