import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ColorPicker } from '../components/ColorPicker'

vi.mock('react-colorful', () => ({
  HexColorPicker: ({ color, onChange }: { color: string; onChange: (c: string) => void }) => (
    <div data-testid="color-picker" data-color={color}>
      <button onClick={() => onChange('#ff0000')}>Change Red</button>
    </div>
  ),
}))

describe('Color Picker', () => {
  it('renders with color value', () => {
    render(<ColorPicker color="#3a7bd5" onChange={() => {}} />)
    expect(screen.getByText('#3a7bd5')).toBeTruthy()
  })

  it('renders with label', () => {
    render(<ColorPicker color="#3a7bd5" onChange={() => {}} label="Theme Color" />)
    expect(screen.getByText('Theme Color')).toBeTruthy()
  })

  it('toggles picker on button click', () => {
    render(<ColorPicker color="#3a7bd5" onChange={() => {}} />)
    
    const button = screen.getByLabelText('Pick color')
    fireEvent.click(button)
    
    expect(screen.getByTestId('color-picker')).toBeTruthy()
  })

  it('calls onChange when color changes', () => {
    const onChange = vi.fn()
    render(<ColorPicker color="#3a7bd5" onChange={onChange} />)
    
    const button = screen.getByLabelText('Pick color')
    fireEvent.click(button)
    
    const changeButton = screen.getByText('Change Red')
    fireEvent.click(changeButton)
    
    expect(onChange).toHaveBeenCalledWith('#ff0000')
  })
})
