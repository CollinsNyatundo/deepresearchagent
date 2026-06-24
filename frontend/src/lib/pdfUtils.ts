import { PDFDocument } from 'pdf-lib'

export async function mergePdfs(pdfs: PDFDocument[]): Promise<PDFDocument> {
  const merged = await PDFDocument.create()
  for (const pdf of pdfs) {
    const pages = await merged.copyPages(pdf, pdf.getPageIndices())
    for (const page of pages) {
      merged.addPage(page)
    }
  }
  return merged
}

export async function splitPdf(pdf: PDFDocument): Promise<PDFDocument[]> {
  const pages = []
  for (let i = 0; i < pdf.getPageCount(); i++) {
    const newPdf = await PDFDocument.create()
    const [page] = await newPdf.copyPages(pdf, [i])
    newPdf.addPage(page)
    pages.push(newPdf)
  }
  return pages
}

export async function extractTextFromPdf(_pdfBytes: Uint8Array): Promise<string> {
  // pdf-lib doesn't support text extraction
  // For actual text extraction, use pdfjs-dist in the browser
  // This is a placeholder that returns empty string
  return ''
}

export async function compressPdf(pdf: PDFDocument): Promise<Uint8Array> {
  const bytes = await pdf.save({ useObjectStreams: true })
  return bytes
}
