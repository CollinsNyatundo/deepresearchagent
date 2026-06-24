import { useCallback } from 'react'
import { ImageDown } from 'lucide-react'
import { exportElementToImage } from '../lib/exportImage'
import { toast } from 'sonner'

interface ExportImageButtonProps {
  targetId: string
  filename?: string
  format?: 'png' | 'svg'
}

export function ExportImageButton({ targetId, filename = 'export', format = 'png' }: ExportImageButtonProps) {
  const handleExport = useCallback(async () => {
    const element = document.getElementById(targetId)
    if (!element) {
      toast.error('Target element not found')
      return
    }
    try {
      await exportElementToImage(element, format, filename)
    } catch (error) {
      toast.error('Export failed')
    }
  }, [targetId, filename, format])

  return (
    <button
      onClick={handleExport}
      className="flex items-center gap-2 px-3 py-2 text-xs rounded-lg bg-white/[0.03] border border-white/[0.06] text-[#c4c6d8] hover:bg-white/[0.06] transition-colors"
      title={`Export as ${format.toUpperCase()}`}
    >
      <ImageDown className="w-3.5 h-3.5" />
      Export
    </button>
  )
}