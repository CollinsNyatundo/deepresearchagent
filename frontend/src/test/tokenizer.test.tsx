import { describe, it, expect, vi } from 'vitest'
import { countTokens, estimateCost, formatTokenCount } from '../lib/tokenizer'

vi.mock('gpt-tokenizer', () => ({
  encode: vi.fn().mockReturnValue(new Array(10)),
}))

describe('GPT Tokenizer', () => {
  it('counts tokens correctly', () => {
    const result = countTokens('Hello world')
    expect(result).toBe(10)
  })

  it('estimates cost for gpt-4', () => {
    const cost = estimateCost(1000, 'gpt-4')
    expect(cost).toBe(0.03)
  })

  it('estimates cost for gpt-3.5-turbo', () => {
    const cost = estimateCost(1000, 'gpt-3.5-turbo')
    expect(cost).toBe(0.0015)
  })

  it('formats small token counts', () => {
    expect(formatTokenCount(500)).toBe('500 tokens')
  })

  it('formats large token counts', () => {
    expect(formatTokenCount(1500)).toBe('1.5k tokens')
  })
})
