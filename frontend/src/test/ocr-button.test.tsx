import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { OcrButton } from '../components/OcrButton'

vi.mock('../lib/ocr', () => ({
  extractTextFromImage: vi.fn().mockResolvedValue({ text: 'Extracted text', confidence: 95 }),
}))

describe('OcrButton', () => {
  it('renders OCR button', () => {
    render(<OcrButton onExtract={() => {}} />)
    expect(screen.getByText('OCR')).toBeTruthy()
  })

  it('shows file input when clicked', () => {
    render(<OcrButton onExtract={() => {}} />)
    const button = screen.getByText('OCR')
    fireEvent.click(button)
    expect(document.querySelector('input[type="file"]')).toBeTruthy()
  })

  it('calls onExtract with extracted text after file upload', async () => {
    const onExtract = vi.fn()
    render(<OcrButton onExtract={onExtract} />)

    const button = screen.getByText('OCR')
    fireEvent.click(button)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['image'], 'test.png', { type: 'image/png' })
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => {
      expect(onExtract).toHaveBeenCalledWith('Extracted text')
    })
  })

  it('shows loading state during extraction', async () => {
    render(<OcrButton onExtract={() => {}} />)

    const button = screen.getByText('OCR')
    fireEvent.click(button)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['image'], 'test.png', { type: 'image/png' })
    fireEvent.change(input, { target: { files: [file] } })

    expect(screen.getByText('Extracting...')).toBeTruthy()
  })
})
