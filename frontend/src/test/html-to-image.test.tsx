import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MarkdownPreview } from '../components/notes/MarkdownPreview'

const mockToPng = vi.fn().mockResolvedValue('data:image/png;base64,test')
const mockToSvg = vi.fn().mockResolvedValue('data:image/svg+xml;base64,test')

vi.mock('html-to-image', () => ({
  toPng: (...args: any[]) => mockToPng(...args),
  toSvg: (...args: any[]) => mockToSvg(...args),
}))

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('html-to-image Export', () => {
  it('renders export buttons when showExport is true', () => {
    render(<MarkdownPreview content="# Test" onNavigate={() => {}} showExport={true} />)
    
    expect(screen.getByText('PNG')).toBeTruthy()
    expect(screen.getByText('SVG')).toBeTruthy()
  })

  it('hides export buttons when showExport is false', () => {
    render(<MarkdownPreview content="# Test" onNavigate={() => {}} showExport={false} />)
    
    expect(screen.queryByText('PNG')).toBeFalsy()
    expect(screen.queryByText('SVG')).toBeFalsy()
  })

  it('calls toPng when PNG export button is clicked', async () => {
    render(<MarkdownPreview content="# Test" onNavigate={() => {}} />)
    
    const pngButton = screen.getByText('PNG')
    fireEvent.click(pngButton)
    
    await vi.waitFor(() => {
      expect(mockToPng).toHaveBeenCalled()
    })
  })

  it('calls toSvg when SVG export button is clicked', async () => {
    render(<MarkdownPreview content="# Test" onNavigate={() => {}} />)
    
    const svgButton = screen.getByText('SVG')
    fireEvent.click(svgButton)
    
    await vi.waitFor(() => {
      expect(mockToSvg).toHaveBeenCalled()
    })
  })
})
