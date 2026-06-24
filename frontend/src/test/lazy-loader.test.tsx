import { describe, it, expect } from 'vitest'
import { lazyLoad } from '../lib/lazyLoader'

describe('Lazy Loading', () => {
  it('returns a lazy-loaded component wrapper', () => {
    const LazyComp = lazyLoad(() => import('../components/AnimatedContainer') as any, { fallback: 'Loading...' })
    expect(LazyComp).toBeDefined()
  })
})
