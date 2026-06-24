import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TokenCounter } from '../components/TokenCounter'

describe('TokenCounter', () => {
  it('displays token count for given text', () => {
    render(<TokenCounter text="Hello world" />)
    expect(screen.getByText(/\d+ tokens/)).toBeTruthy()
  })

  it('displays cost estimate for gpt-4', () => {
    render(<TokenCounter text="Hello world" model="gpt-4" />)
    expect(screen.getByText(/\$[\d.]+/)).toBeTruthy()
  })

  it('updates when text changes', () => {
    const { rerender } = render(<TokenCounter text="short" />)
    const before = screen.getByTestId('token-count').textContent
    rerender(<TokenCounter text="this is a much longer text with many more tokens to count" />)
    const after = screen.getByTestId('token-count').textContent
    expect(after).not.toBe(before)
  })

  it('shows warning when approaching token limit', () => {
    const longText = 'a '.repeat(4000) // ~4000 tokens
    render(<TokenCounter text={longText} maxTokens={4096} />)
    expect(screen.getByTestId('token-warning')).toBeTruthy()
  })
})
