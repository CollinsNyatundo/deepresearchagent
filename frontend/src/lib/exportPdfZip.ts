import { jsPDF } from 'jspdf'
import { toast } from 'sonner'

export async function exportToPdf(element: HTMLElement, filename: string = 'document'): Promise<void> {
  try {
    const doc = new jsPDF({
      orientation: 'portrait',
      unit: 'px',
      format: [element.scrollWidth + 40, element.scrollHeight + 40],
      putOnlyUsedFonts: true,
      floatPrecision: 16,
    })
    
    doc.setFillColor(26, 26, 46)
    doc.rect(0, 0, doc.internal.pageSize.getWidth(), doc.internal.pageSize.getHeight(), 'F')
    
    await doc.html(element, {
      x: 20,
      y: 20,
      html2canvas: {
        scale: 0.5,
        backgroundColor: '#1a1a2e',
        useCORS: true,
      },
      callback: (pdf) => {
        pdf.save(`${filename}.pdf`)
        toast.success('Exported as PDF')
      },
    })
  } catch (error) {
    toast.error(`PDF export failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    throw error
  }
}

export async function exportToZip(files: { name: string; content: string | Blob }[], filename: string = 'archive'): Promise<void> {
  try {
    const JSZip = (await import('jszip')).default
    const zip = new JSZip()
    
    for (const file of files) {
      if (typeof file.content === 'string') {
        zip.file(file.name, file.content)
      } else {
        zip.file(file.name, file.content)
      }
    }
    
    const blob = await zip.generateAsync({ type: 'blob' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${filename}.zip`
    link.click()
    URL.revokeObjectURL(url)
    
    toast.success('Exported as ZIP')
  } catch (error) {
    toast.error(`ZIP export failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    throw error
  }
}
