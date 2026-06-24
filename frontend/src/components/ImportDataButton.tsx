import { useState, useRef, ChangeEvent } from 'react'
import { FileSpreadsheet } from 'lucide-react'
import { parseSpreadsheet, ParsedData } from '../lib/importSpreadsheet'
import { toast } from 'sonner'

interface ImportDataButtonProps {
  onDataLoaded: (data: ParsedData) => void
}

export function ImportDataButton({ onDataLoaded }: ImportDataButtonProps) {
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
      const data = await parseSpreadsheet(file)
      onDataLoaded(data)
      toast.success(`Imported ${data.rows.length} rows`)
    } catch (error) {
      toast.error('Failed to import file')
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
        accept=".csv,.xlsx,.xls"
        onChange={handleFileChange}
        className="hidden"
      />
      <button
        onClick={handleClick}
        disabled={isLoading}
        className="flex items-center gap-2 px-3 py-2 text-xs rounded-lg bg-white/[0.03] border border-white/[0.06] text-[#c4c6d8] hover:bg-white/[0.06] transition-colors disabled:opacity-50"
      >
        <FileSpreadsheet className="w-3.5 h-3.5" />
        {isLoading ? 'Importing...' : 'Import Data'}
      </button>
    </>
  )
}