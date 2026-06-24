import { Component, type ReactNode } from 'react'

interface Props { children: ReactNode; fallback?: ReactNode }
interface State { hasError: boolean; error?: Error }

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return (
        <div className="flex items-center justify-center h-full p-6">
          <div className="text-center max-w-md liquid-glass rounded-2xl p-6">
            <h2 className="text-lg font-semibold text-[#c45a5a] mb-2">Something went wrong</h2>
            <p className="text-sm text-[#999] mb-4">{this.state.error?.message || 'An unexpected error occurred'}</p>
            <button
              onClick={() => this.setState({ hasError: false })}
              className="px-4 py-2 rounded-xl text-sm bg-[#c8956c]/15 text-[#c8956c] hover:bg-[#c8956c]/25 cursor-pointer border-none transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
