import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CompareVersions } from '../components/CompareVersions'

describe('Compare Versions', () => {
  it('renders diff viewer with two versions', () => {
    render(
      <CompareVersions
        oldText="Hello world\nLine 2"
        newText="Hello world\nModified line"
      />
    )
    expect(screen.getByText(/added/i)).toBeTruthy()
    expect(screen.getByText(/removed/i)).toBeTruthy()
  })

  it('shows diff statistics', () => {
    render(
      <CompareVersions
        oldText="Line one\nLine two"
        newText="Line one\nModified line\nNew line"
      />
    )
    expect(screen.getByText(/added/i)).toBeTruthy()
    expect(screen.getByText(/removed/i)).toBeTruthy()
  })
})
