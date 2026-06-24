import { describe, it, expect } from 'vitest'
import { safeEvaluate } from '../lib/mathUtils'

describe('Math Utils', () => {
  it('evaluates simple expressions', () => {
    expect(safeEvaluate('2 + 2')).toBe(4)
    expect(safeEvaluate('10 * 5')).toBe(50)
  })

  it('returns error for invalid expressions', () => {
    expect(safeEvaluate('invalid')).toBe('Error')
  })
})
