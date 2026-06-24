import { describe, it, expect } from 'vitest'
import { formatDate } from '../lib/dateUtils'

describe('Date Utils', () => {
  it('formats date string', () => {
    const result = formatDate('2024-01-15')
    expect(result).toBe('2024-01-15 00:00')
  })

  it('returns invalid for bad date', () => {
    expect(formatDate('invalid')).toBe('Invalid date')
  })
})
