import { type ReactNode, useState, useEffect } from 'react'
import Header from './Header'
import NavRail from './NavRail'
import BackgroundRenderer from '../backgrounds/BackgroundRenderer'
import { ErrorBoundary } from '../ErrorBoundary'

interface LayoutProps {
  sidebar: ReactNode
  children: ReactNode
  userEmail?: string
  onSignOut?: () => void
  /** The module id this layout belongs to — used to sync the NavRail active state */
  moduleId?: string
}

const SIDEBAR_KEY = 'dra_sidebar_expanded'

export default function Layout({ sidebar, children, userEmail, onSignOut, moduleId }: LayoutProps) {
  const [expandedModule, setExpandedModule] = useState<string | null>(() => {
    try {
      const saved = localStorage.getItem(SIDEBAR_KEY)
      return saved !== null ? saved : (moduleId ?? 'research')
    } catch {
      return moduleId ?? 'research'
    }
  })

  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    try {
      if (expandedModule !== null) {
        localStorage.setItem(SIDEBAR_KEY, expandedModule)
      } else {
        localStorage.removeItem(SIDEBAR_KEY)
      }
    } catch { /* ignore */ }
  }, [expandedModule])

  const handleToggleModule = (id: string) => {
    setExpandedModule(prev => {
      // If this module is already the expanded one, toggle collapse
      if (prev === id) return null
      return id
    })
    setMobileOpen(false)
  }

  const isSidebarExpanded = expandedModule !== null

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
          onToggleSidebar={() => setMobileOpen(!mobileOpen)}
        />
      </div>

      {/* Body — z-10 */}
      <div className="flex-1 flex overflow-hidden z-10 relative">
        {/* Mobile overlay */}
        {mobileOpen && (
          <div
            className="lg:hidden fixed inset-0 bg-black/60 z-20 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
        )}

        {/* Nav Rail — always visible, 48px */}
        <div className="hidden lg:block z-30 relative">
          <NavRail
            userEmail={userEmail}
            onSignOut={onSignOut}
            expandedModule={expandedModule}
            onToggleModule={handleToggleModule}
          />
        </div>

        {/* Sidebar Panel — collapses to 0, expands to 240px */}
        <aside
          className={`sidebar-panel border-r border-white/[0.06] z-30 relative flex flex-col
            ${isSidebarExpanded ? 'expanded w-[15rem]' : 'collapsed'}
            ${mobileOpen ? 'fixed left-0 top-0 h-full w-[15rem] z-30 lg:relative lg:z-auto' : 'hidden lg:flex'}
          `}
          style={{ background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(8px) saturate(130%)' }}
        >
          <div className="w-[15rem] h-full overflow-hidden">
            {sidebar}
          </div>
        </aside>

        {/* Mobile sidebar (overlay) */}
        {mobileOpen && (
          <aside className="lg:hidden fixed left-12 top-0 h-full w-[15rem] z-30 flex flex-col border-r border-white/[0.06]"
            style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(12px)' }}
          >
            <div className="w-[15rem] h-full overflow-hidden">
              {sidebar}
            </div>
          </aside>
        )}

        {/* Main content */}
        <main className="flex-1 overflow-hidden flex flex-col">
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
