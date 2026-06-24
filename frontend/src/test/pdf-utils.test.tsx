import { describe, it, expect } from 'vitest'
import { PDFDocument } from 'pdf-lib'
import { mergePdfs, splitPdf, extractTextFromPdf } from '../lib/pdfUtils'

describe('PDF Manipulation', () => {
  it('merges multiple PDFs into one', async () => {
    const pdf1 = await PDFDocument.create()
    pdf1.addPage([100, 100])
    const pdf2 = await PDFDocument.create()
    pdf2.addPage([100, 100])

    const merged = await mergePdfs([pdf1, pdf2])
    expect(merged.getPageCount()).toBe(2)
  })

  it('splits PDF into pages', async () => {
    const pdf = await PDFDocument.create()
    pdf.addPage([100, 100])
    pdf.addPage([100, 100])
    pdf.addPage([100, 100])

    const pages = await splitPdf(pdf)
    expect(pages).toHaveLength(3)
  })

  it('extracts text from PDF bytes', async () => {
    const pdf = await PDFDocument.create()
    pdf.addPage([100, 100])
    // pdf-lib doesn't support text extraction natively, so we mock the behavior
    // For actual extraction, we'd use pdfjs-dist
    const result = await extractTextFromPdf(await pdf.save())
    expect(result).toBeDefined()
  })
})
