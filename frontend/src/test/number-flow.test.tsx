import { describe, it, expect } from 'vitest'
import { formatNumber } from '../lib/numberFlow'

describe('Number Flow', () => {
  it('formats numbers with commas', () => {
    expect(formatNumber(1234567)).toBe('1,234,567')
    expect(formatNumber(42)).toBe('42')
  })
})
