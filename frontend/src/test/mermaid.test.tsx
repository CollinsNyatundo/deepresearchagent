import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MarkdownPreview } from '../components/notes/MarkdownPreview'

vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn().mockResolvedValue({ svg: '<svg>diagram</svg>' }),
  },
}))

describe('Mermaid Diagram Rendering', () => {
  it('renders mermaid code blocks as diagrams', async () => {
    const content = '\`\`\`mermaid\ngraph TD\nA-->B\n\`\`\`'
    render(<MarkdownPreview content={content} onNavigate={() => {}} />)
    
    await waitFor(() => {
      const diagram = document.querySelector('.mermaid')
      expect(diagram).toBeTruthy()
    })
  })

  it('handles mermaid syntax errors gracefully', async () => {
    const mermaid = await import('mermaid')
    vi.mocked(mermaid.default.render).mockRejectedValueOnce(new Error('Invalid syntax'))
    
    const content = '\`\`\`mermaid\ninvalid\n\`\`\`'
    render(<MarkdownPreview content={content} onNavigate={() => {}} />)
    
    await waitFor(() => {
      const error = screen.queryByText(/Mermaid error/i)
      expect(error).toBeTruthy()
    })
  })

  it('renders non-mermaid code blocks with syntax highlighting', () => {
    const content = '\`\`\`typescript\nconst x = 1;\n\`\`\`'
    render(<MarkdownPreview content={content} onNavigate={() => {}} />)
    
    expect(document.querySelector('pre')).toBeTruthy()
    expect(document.querySelector('.mermaid')).toBeFalsy()
  })
})
