import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router'
import { Command } from 'cmdk'
import { FileText, BookOpen, FlaskConical } from 'lucide-react'

export default function CommandPalette() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [])

  const handleSelect = useCallback((value: string) => {
    setOpen(false)
    navigate(value)
  }, [navigate])

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Global Command Palette"
      className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-[100] w-full max-w-[640px]"
    >
      <div className="liquid-glass rounded-2xl overflow-hidden border border-white/[0.06] shadow-2xl">
        <Command.Input
          placeholder="Search or navigate..."
          className="w-full bg-transparent border-b border-white/[0.06] px-4 py-3 text-[#e0e0e0] placeholder:text-[#555] focus:outline-none"
        />
        <Command.List className="max-h-[400px] overflow-y-auto p-2">
          <Command.Empty className="py-6 text-center text-sm text-[#555]">
            No results found.
          </Command.Empty>

          <Command.Group heading="Navigation">
            <Command.Item
              value="/research"
              onSelect={() => handleSelect('/research')}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-[#e0e0e0] hover:bg-white/[0.06] cursor-pointer"
            >
              <FlaskConical className="w-4 h-4 text-[#c8956c]" />
              Research
            </Command.Item>
            <Command.Item
              value="/notes"
              onSelect={() => handleSelect('/notes')}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-[#e0e0e0] hover:bg-white/[0.06] cursor-pointer"
            >
              <FileText className="w-4 h-4 text-[#c8956c]" />
              Notes
            </Command.Item>
            <Command.Item
              value="/documents"
              onSelect={() => handleSelect('/documents')}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-[#e0e0e0] hover:bg-white/[0.06] cursor-pointer"
            >
              <BookOpen className="w-4 h-4 text-[#c8956c]" />
              Documents
            </Command.Item>
          </Command.Group>
        </Command.List>
      </div>
    </Command.Dialog>
  )
}
