import { describe, it, expect, vi } from 'vitest'
import { initializeOnDeviceAI, detectPII, analyzeSentiment } from '../lib/onDeviceAI'

vi.mock('@huggingface/transformers', () => ({
  pipeline: vi.fn().mockResolvedValue(
    vi.fn().mockResolvedValue([
      { label: 'POSITIVE', score: 0.95 },
    ])
  ),
  env: {
    cacheDir: '',
    allowLocalModels: false,
    allowRemoteModels: false,
  },
}))

describe('On-Device AI Features', () => {
  it('initializes IndexedDB caching', async () => {
    const { env } = await import('@huggingface/transformers')
    await initializeOnDeviceAI()
    expect(env.cacheDir).toBe('indexeddb://transformers-cache')
    expect(env.allowLocalModels).toBe(true)
    expect(env.allowRemoteModels).toBe(true)
  })

  it('detects PII in text', async () => {
    const result = await detectPII('John Smith lives at 123 Main St')
    expect(result).toBeDefined()
    expect(Array.isArray(result)).toBe(true)
  })

  it('analyzes sentiment of text', async () => {
    const result = await analyzeSentiment('This is great!')
    expect(result).toBeDefined()
    expect(result.label).toBe('POSITIVE')
  })
})
