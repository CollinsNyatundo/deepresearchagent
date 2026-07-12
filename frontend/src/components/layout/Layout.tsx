import { type ReactNode } from 'react'
import Sidebar from './Sidebar'
import BackgroundRenderer from '../backgrounds/BackgroundRenderer'
import { ErrorBoundary } from '../ErrorBoundary'

interface LayoutProps {
  sidebar?: ReactNode
  children: ReactNode
  userEmail?: string
  onSignOut?: () => void
  moduleId?: string
}

export default function Layout({ sidebar, children }: LayoutProps) {
  return (
    <div className="h-screen w-screen flex overflow-hidden bg-black relative">
      {/* Background layer — z-0 */}
      <div className="absolute inset-0 z-0">
        <BackgroundRenderer />
      </div>

      {/* Body — z-10 */}
      <div className="flex-1 flex overflow-hidden z-10 relative">
        {/* Unified Left Sidebar */}
        <Sidebar>
          {sidebar}
        </Sidebar>

        {/* Main content */}
        <main className="flex-1 overflow-hidden flex flex-col relative bg-transparent">
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </div>
    </div>
  )
}

