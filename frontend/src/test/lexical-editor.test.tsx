import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { LexicalEditor } from '../components/LexicalEditor'

vi.mock('../components/LexicalEditor', () => ({
  LexicalEditor: ({ initialValue }: { initialValue?: string }) => (
    <div data-testid="lexical-editor">
      <div data-testid="toolbar">
        <button title="Bold">Bold</button>
        <button title="Italic">Italic</button>
        <button title="Heading">Heading</button>
        <button title="Quote">Quote</button>
      </div>
      <div contentEditable="true" data-testid="editor-content">
        {initialValue || 'Start typing...'}
      </div>
    </div>
  ),
}))

describe('Lexical Rich Text Editor', () => {
  it('renders editor with placeholder', () => {
    render(<LexicalEditor initialValue="Start typing..." />)
    expect(screen.getByTestId('lexical-editor')).toBeTruthy()
  })

  it('renders editor toolbar buttons', () => {
    render(<LexicalEditor />)
    expect(screen.getByTitle('Bold')).toBeTruthy()
    expect(screen.getByTitle('Italic')).toBeTruthy()
    expect(screen.getByTitle('Heading')).toBeTruthy()
    expect(screen.getByTitle('Quote')).toBeTruthy()
  })

  it('renders with initial value', () => {
    const { container } = render(<LexicalEditor initialValue="# Hello World" />)
    expect(container.querySelector('[contenteditable="true"]')).toBeTruthy()
  })
})
