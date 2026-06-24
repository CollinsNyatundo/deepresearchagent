import { createTwoFilesPatch } from 'diff'

export interface DiffResult {
  unified: string
  added: number
  removed: number
  unchanged: number
}

export function computeDiff(oldText: string, newText: string, context: number = 3): DiffResult {
  const patch = createTwoFilesPatch('old', 'new', oldText, newText, undefined, undefined, { context })
  
  const lines = patch.split('\n')
  let added = 0
  let removed = 0
  let unchanged = 0
  
  for (const line of lines) {
    if (line.startsWith('+') && !line.startsWith('+++')) {
      added++
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      removed++
    } else if (!line.startsWith('@@') && !line.startsWith('+++') && !line.startsWith('---') && line.length > 0) {
      unchanged++
    }
  }
  
  return { unified: patch, added, removed, unchanged }
}

export function renderDiffToHtml(diff: DiffResult): string {
  const lines = diff.unified.split('\n')
  return lines.map((line) => {
    if (line.startsWith('+') && !line.startsWith('+++')) {
      return `<span class="diff-add">${escapeHtml(line)}</span>`
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      return `<span class="diff-remove">${escapeHtml(line)}</span>`
    } else if (line.startsWith('@@')) {
      return `<span class="diff-hunk">${escapeHtml(line)}</span>`
    } else {
      return `<span class="diff-context">${escapeHtml(line)}</span>`
    }
  }).join('\n')
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}
