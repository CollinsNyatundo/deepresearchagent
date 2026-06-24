import { useState, useRef, ChangeEvent } from 'react'
import { FileText, Loader } from 'lucide-react'
import { extractTextFromImage } from '../lib/ocr'
import { toast } from 'sonner'

interface OcrButtonProps {
  onExtract: (text: string) => void
}

export function OcrButton({ onExtract }: OcrButtonProps) {
  const [isLoading, setIsLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleClick = () => {
    inputRef.current?.click()
  }

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsLoading(true)
    try {
      const result = await extractTextFromImage(file)
      onExtract(result.text)
      toast.success(`OCR complete (${Math.round(result.confidence)}% confidence)`)
    } catch (error) {
      toast.error('OCR failed')
    } finally {
      setIsLoading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />
      <button
        onClick={handleClick}
        disabled={isLoading}
        className="flex items-center gap-2 px-3 py-2 text-xs rounded-lg bg-white/[0.03] border border-white/[0.06] text-[#c4c6d8] hover:bg-white/[0.06] transition-colors disabled:opacity-50"
      >
        {isLoading ? <Loader className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
        {isLoading ? 'Extracting...' : 'OCR'}
      </button>
    </>
  )
}
