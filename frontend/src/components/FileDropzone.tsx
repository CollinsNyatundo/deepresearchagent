import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload } from 'lucide-react'
import { toast } from 'sonner'

interface FileDropzoneProps {
  onFilesAccepted: (files: File[]) => void
  accept?: Record<string, string[]>
  maxFiles?: number
  maxSize?: number
}

export function FileDropzone({
  onFilesAccepted,
  accept = { 'text/markdown': ['.md'], 'text/plain': ['.txt'] },
  maxFiles = 5,
  maxSize = 5 * 1024 * 1024,
}: FileDropzoneProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      if (rejectedFiles.length > 0) {
        rejectedFiles.forEach((file) => {
          const errors = file.errors.map((e: any) => e.message).join(', ')
          toast.error(`Rejected: ${file.file.name} - ${errors}`)
        })
      }
      if (acceptedFiles.length > 0) {
        onFilesAccepted(acceptedFiles)
        toast.success(`${acceptedFiles.length} file(s) uploaded`)
      }
    },
    [onFilesAccepted]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    maxFiles,
    maxSize,
  })

  return (
    <div
      {...getRootProps()}
      className={`
        border-2 border-dashed rounded-lg p-6 cursor-pointer transition-colors
        ${isDragActive
          ? 'border-[#3a7bd5] bg-[#3a7bd5]/10'
          : 'border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.02)] hover:bg-[rgba(255,255,255,0.04)]'
        }
      `}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-2 text-[#c4c6d8]">
        <Upload size={24} className={isDragActive ? 'text-[#3a7bd5]' : ''} />
        <p className="text-sm">
          {isDragActive
            ? 'Drop files here...'
            : 'Drag & drop files here, or click to select'}
        </p>
        <p className="text-xs text-[#c4c6d8]/60">
          Max {maxFiles} files, up to {Math.round(maxSize / 1024 / 1024)}MB each
        </p>
      </div>
    </div>
  )
}
