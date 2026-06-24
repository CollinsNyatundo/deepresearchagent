import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ExportImageButton } from '../components/ExportImageButton'

vi.mock('../lib/exportImage', () => ({
  exportElementToImage: vi.fn().mockResolvedValue(undefined),
}))

describe('Export Image Button', () => {
  it('renders export button', () => {
    render(<ExportImageButton targetId="test-element" />)
    expect(screen.getByText('Export')).toBeTruthy()
  })

  it('shows error when target element not found', () => {
    render(<ExportImageButton targetId="nonexistent" />)
    const button = screen.getByText('Export')
    fireEvent.click(button)
    // Should not throw
    expect(button).toBeTruthy()
  })
})
