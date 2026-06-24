import { describe, it, expect } from 'vitest'
import { lazyLoad } from '../lib/lazyLoader'

describe('Lazy Loading Applied', () => {
  it('lazy loads MarkdownPreview component', async () => {
    const LazyMarkdownPreview = lazyLoad(
      () => import('../components/notes/MarkdownPreview') as any,
      { fallback: <div>Loading preview...</div> }
    )
    expect(LazyMarkdownPreview).toBeDefined()
  })

  it('lazy loads LexicalEditor component', async () => {
    const LazyLexicalEditor = lazyLoad(
      () => import('../components/LexicalEditor') as any,
      { fallback: <div>Loading editor...</div> }
    )
    expect(LazyLexicalEditor).toBeDefined()
  })
})
