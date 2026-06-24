import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { useDropzone } from 'react-dropzone'
import { FileDropzone } from '../components/FileDropzone'

vi.mock('react-dropzone', () => ({
  useDropzone: vi.fn(),
}))

describe('File Dropzone', () => {
  it('renders dropzone with default text', () => {
    vi.mocked(useDropzone).mockReturnValue({
      getRootProps: () => ({ onClick: vi.fn() }),
      getInputProps: () => ({ onChange: vi.fn() }),
      isDragActive: false,
    } as any)

    render(<FileDropzone onFilesAccepted={() => {}} />)
    expect(screen.getByText(/Drag & drop files here/i)).toBeTruthy()
  })

  it('shows drag active state', () => {
    vi.mocked(useDropzone).mockReturnValue({
      getRootProps: () => ({ onClick: vi.fn() }),
      getInputProps: () => ({ onChange: vi.fn() }),
      isDragActive: true,
    } as any)

    render(<FileDropzone onFilesAccepted={() => {}} />)
    expect(screen.getByText(/Drop files here/i)).toBeTruthy()
  })
})
