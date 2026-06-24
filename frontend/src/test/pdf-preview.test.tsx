import { describe, it, expect, vi } from 'vitest'
import { renderPdfPage, getPdfPageCount } from '../lib/pdfPreview'

vi.mock('pdfjs-dist', () => {
  const getPage = vi.fn().mockResolvedValue({
    getViewport: vi.fn().mockReturnValue({ width: 100, height: 100 }),
    render: vi.fn().mockReturnValue({ promise: Promise.resolve() }),
  })
  return {
    getDocument: vi.fn().mockReturnValue({
      promise: Promise.resolve({
        numPages: 3,
        getPage,
      }),
    }),
    GlobalWorkerOptions: { workerSrc: '' },
  }
})

describe('PDF Preview', () => {
  it('gets page count from PDF bytes', async () => {
    const count = await getPdfPageCount(new Uint8Array([1, 2, 3]))
    expect(count).toBe(3)
  })

  it('renders PDF page to canvas', async () => {
    const { getDocument } = await import('pdfjs-dist')
    const canvas = document.createElement('canvas')
    await renderPdfPage(new Uint8Array([1, 2, 3]), 1, canvas)
    
    const pdf = await vi.mocked(getDocument)({} as any).promise
    expect(pdf.getPage).toHaveBeenCalledWith(1)
  })
})
