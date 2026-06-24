import * as pdfjs from 'pdfjs-dist'

// Set worker source - in production this would be a CDN or bundled worker
pdfjs.GlobalWorkerOptions.workerSrc = ''

export async function getPdfPageCount(pdfBytes: Uint8Array): Promise<number> {
  const loadingTask = pdfjs.getDocument({ data: pdfBytes })
  const pdf = await loadingTask.promise
  return pdf.numPages
}

export async function renderPdfPage(
  pdfBytes: Uint8Array,
  pageNumber: number,
  canvas: HTMLCanvasElement,
  scale: number = 1.5
): Promise<void> {
  const loadingTask = pdfjs.getDocument({ data: pdfBytes })
  const pdf = await loadingTask.promise
  const page = await pdf.getPage(pageNumber)
  
  const viewport = page.getViewport({ scale })
  canvas.width = viewport.width
  canvas.height = viewport.height
  
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  await page.render({ canvasContext: ctx, viewport, canvas }).promise
}
