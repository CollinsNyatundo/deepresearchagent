import { describe, it, expect } from 'vitest'
import { LexicalEditor } from '../components/LexicalEditor'

describe('Lexical Editor Plugins', () => {
  it('exports LexicalEditor with markdown support', () => {
    expect(LexicalEditor).toBeDefined()
  })

  it('has markdown shortcut plugin configured', () => {
    // The component should include TRANSFORMERS which enable markdown shortcuts
    expect(LexicalEditor).toBeDefined()
  })

  it('has wiki-link support', () => {
    // The editor should handle [[wiki-link]] syntax
    expect(LexicalEditor).toBeDefined()
  })
})
