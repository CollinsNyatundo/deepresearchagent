import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MarkdownPreview } from '../components/notes/MarkdownPreview'

vi.mock('jspdf', () => {
  class MockJsPDF {
    html = vi.fn().mockResolvedValue(undefined)
    save = vi.fn()
    internal = { pageSize: { getWidth: () => 800, getHeight: () => 600 } }
    setFillColor = vi.fn()
    rect = vi.fn()
  }
  return { jsPDF: MockJsPDF }
})

vi.mock('jszip', () => {
  class MockJSZip {
    file = vi.fn()
    generateAsync = vi.fn().mockResolvedValue(new Blob(['test']))
  }
  return { default: MockJSZip }
})

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('PDF and ZIP Export', () => {
  it('renders PDF export button', () => {
    render(<MarkdownPreview content="# Test" onNavigate={() => {}} />)
    expect(screen.getByText('PDF')).toBeTruthy()
  })

  it('renders ZIP export button', () => {
    render(<MarkdownPreview content="# Test" onNavigate={() => {}} />)
    expect(screen.getByText('ZIP')).toBeTruthy()
  })

  it('does not throw when PDF export button is clicked', async () => {
    render(<MarkdownPreview content="# Test" onNavigate={() => {}} />)
    
    const pdfButton = screen.getByText('PDF')
    expect(() => fireEvent.click(pdfButton)).not.toThrow()
  })

  it('does not throw when ZIP export button is clicked', async () => {
    render(<MarkdownPreview content="# Test" onNavigate={() => {}} />)
    
    const zipButton = screen.getByText('ZIP')
    expect(() => fireEvent.click(zipButton)).not.toThrow()
  })
})
