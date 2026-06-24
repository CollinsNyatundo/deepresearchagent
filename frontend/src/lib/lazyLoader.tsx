import { lazy, Suspense, ComponentType, ReactNode } from 'react'

interface LazyLoadOptions {
  fallback?: ReactNode
  ssr?: boolean
}

export function lazyLoad<T extends ComponentType<any>>(
  factory: () => Promise<{ default: T }>,
  options: LazyLoadOptions = {}
) {
  const { fallback = null } = options
  const LazyComponent = lazy(factory)

  return function LazyLoadedComponent(props: React.ComponentProps<T>) {
    return (
      <Suspense fallback={fallback}>
        <LazyComponent {...props} />
      </Suspense>
    )
  }
}
