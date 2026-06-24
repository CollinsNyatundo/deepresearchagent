import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ImportDataButton } from '../components/ImportDataButton'

describe('Import Data Button', () => {
  it('renders import button', () => {
    render(<ImportDataButton onDataLoaded={() => {}} />)
    expect(screen.getByText('Import Data')).toBeTruthy()
  })

  it('shows file input when clicked', () => {
    render(<ImportDataButton onDataLoaded={() => {}} />)
    const button = screen.getByText('Import Data')
    fireEvent.click(button)
    expect(document.querySelector('input[type="file"]')).toBeTruthy()
  })
})
