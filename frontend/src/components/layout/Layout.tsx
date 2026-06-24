import { type ReactNode, useState } from 'react'
import Header from './Header'
import Sidebar from './Sidebar'
import BackgroundRenderer from '../backgrounds/BackgroundRenderer'
import { ErrorBoundary } from '../ErrorBoundary'

interface LayoutProps {
  sidebar: ReactNode
  children: ReactNode
  userEmail?: string
  onSignOut?: () => void
}

export default function Layout({ sidebar, children, userEmail, onSignOut }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-black relative">
      {/* Background layer — z-0 */}
      <div className="absolute inset-0 z-0">
        <BackgroundRenderer />
      </div>

      {/* Header — z-10 */}
      <div className="z-10 relative">
        <Header
          userEmail={userEmail}
          onSignOut={onSignOut}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        />
      </div>

      {/* Body — z-10 */}
      <div className="flex-1 flex overflow-hidden z-10 relative">
        {/* Sidebar — 240px, liquid-glass */}
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)}>
          {sidebar}
        </Sidebar>

        {/* 1px gap */}
        <div className="w-px flex-shrink-0 hidden lg:block" />

        {/* Main content */}
        <main className="flex-1 overflow-hidden flex flex-col">
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
