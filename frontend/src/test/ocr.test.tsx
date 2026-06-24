import { describe, it, expect, vi } from 'vitest'
import { extractTextFromImage } from '../lib/ocr'

vi.mock('tesseract.js', () => ({
  createWorker: vi.fn().mockResolvedValue({
    recognize: vi.fn().mockResolvedValue({
      data: {
        text: 'Extracted text',
        confidence: 95,
      },
    }),
    terminate: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('OCR Text Extraction', () => {
  it('extracts text from image', async () => {
    const result = await extractTextFromImage('https://example.com/image.png')
    
    expect(result.text).toBe('Extracted text')
    expect(result.confidence).toBe(95)
  })

  it('handles Blob input', async () => {
    const blob = new Blob(['test'], { type: 'image/png' })
    const result = await extractTextFromImage(blob)
    
    expect(result.text).toBe('Extracted text')
  })
})
