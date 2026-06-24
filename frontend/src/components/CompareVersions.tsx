import { useMemo } from 'react'
import { computeDiff, renderDiffToHtml, DiffResult } from '../lib/textDiff'
import { Diff } from 'lucide-react'

interface CompareVersionsProps {
  oldText: string
  newText: string
}

export function CompareVersions({ oldText, newText }: CompareVersionsProps) {
  const diff: DiffResult = useMemo(() => computeDiff(oldText, newText), [oldText, newText])

  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-white/[0.06]">
        <Diff className="w-4 h-4 text-[#c8956c]" />
        <span className="text-sm font-medium text-[#e0e0e0]">Version Comparison</span>
        <div className="ml-auto flex gap-3 text-xs">
          <span className="text-green-400">+{diff.added} added</span>
          <span className="text-red-400">-{diff.removed} removed</span>
          <span className="text-[#555]">{diff.unchanged} unchanged</span>
        </div>
      </div>
      <div
        className="p-4 font-mono text-sm whitespace-pre overflow-x-auto"
        dangerouslySetInnerHTML={{ __html: renderDiffToHtml(diff) }}
      />
    </div>
  )
}