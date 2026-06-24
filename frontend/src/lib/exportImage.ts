import { toPng, toSvg } from 'html-to-image'
import { toast } from 'sonner'

export type ExportFormat = 'png' | 'svg'

export async function exportElementToImage(
  element: HTMLElement,
  format: ExportFormat = 'png',
  filename: string = 'export'
): Promise<void> {
  try {
    const dataUrl = format === 'png'
      ? await toPng(element, { quality: 0.95, backgroundColor: '#1a1a2e' })
      : await toSvg(element, { backgroundColor: '#1a1a2e' })
    
    const link = document.createElement('a')
    link.download = `${filename}.${format}`
    link.href = dataUrl
    link.click()
    
    toast.success(`Exported as ${format.toUpperCase()}`)
  } catch (error) {
    toast.error(`Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    throw error
  }
}

export function useExportImage() {
  return {
    exportToPng: (element: HTMLElement, filename?: string) => 
      exportElementToImage(element, 'png', filename),
    exportToSvg: (element: HTMLElement, filename?: string) => 
      exportElementToImage(element, 'svg', filename),
  }
}
