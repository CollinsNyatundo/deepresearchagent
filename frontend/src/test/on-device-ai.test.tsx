import { describe, it, expect, vi } from 'vitest'
import { generateText, summarizeText } from '../lib/onDeviceAI'

vi.mock('@huggingface/transformers', () => ({
  pipeline: vi.fn().mockResolvedValue(
    Object.assign(
      vi.fn().mockResolvedValue([
        { generated_text: 'Generated response', score: 0.95 },
      ]),
      { __call__: vi.fn() }
    )
  ),
  env: {
    cacheDir: '',
    allowLocalModels: false,
    allowRemoteModels: false,
  },
}))

describe('On-Device AI', () => {
  it('generates text from prompt', async () => {
    const { pipeline } = await import('@huggingface/transformers')
    vi.mocked(pipeline).mockResolvedValueOnce(
      Object.assign(
        vi.fn().mockResolvedValue([
          { generated_text: 'Generated response', score: 0.95 },
        ]),
        { __call__: vi.fn() }
      ) as any
    )
    
    const results = await generateText('Hello', 10)
    
    expect(results).toHaveLength(1)
    expect(results[0].text).toBe('Generated response')
  })

  it('summarizes text', async () => {
    const { pipeline } = await import('@huggingface/transformers')
    vi.mocked(pipeline).mockResolvedValueOnce(
      Object.assign(
        vi.fn().mockResolvedValue([
          { summary_text: 'Short summary' },
        ]),
        { __call__: vi.fn() }
      ) as any
    )
    
    const result = await summarizeText('Long text to summarize...', 50)
    
    expect(result).toBe('Short summary')
  })
})
