import { Link, useLocation } from 'react-router'
import { Diamond, Menu } from 'lucide-react'
import BackgroundSwitcher from '../backgrounds/BackgroundSwitcher'

interface HeaderProps {
  userEmail?: string
  onSignOut?: () => void
  onToggleSidebar?: () => void
}

export default function Header({ userEmail, onSignOut, onToggleSidebar }: HeaderProps) {
  const location = useLocation()
  const path = location.pathname

  const modules = [
    { id: 'research', label: 'Research', path: '/research' },
    { id: 'notes', label: 'Notes', path: '/notes' },
    { id: 'documents', label: 'Documents', path: '/documents' },
  ] as const

  return (
    <header className="h-[2.75rem] flex-shrink-0 liquid-glass z-10 relative flex items-center px-4 gap-4">
      {/* Mobile sidebar toggle */}
      {onToggleSidebar && (
        <button
          onClick={onToggleSidebar}
          className="lg:hidden text-[#999] hover:text-[#e0e0e0] transition-colors cursor-pointer bg-transparent border-none p-1"
          title="Toggle sidebar"
        >
          <Menu className="w-4 h-4" />
        </button>
      )}

      {/* Brand */}
      <Link to="/research" className="flex items-center gap-2 shrink-0">
        <Diamond className="w-4 h-4 text-[#c8956c]" strokeWidth={1.5} />
        <span className="text-sm font-semibold text-[#e0e0e0] tracking-tight hidden sm:inline">
          DeepResearch<span className="text-[#c8956c]">.ai</span>
        </span>
      </Link>

      {/* Module Switcher */}
      <nav className="flex items-center gap-0.5 bg-white/[0.03] rounded-xl p-0.5">
        {modules.map((mod) => {
          const isActive = path === mod.path || path.startsWith(mod.path + '/')
          return (
            <Link
              key={mod.id}
              to={mod.path}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-white/[0.06] text-[#e0e0e0]'
                  : 'text-[#555] hover:text-[#999]'
              }`}
            >
              {mod.label}
            </Link>
          )
        })}
      </nav>

      {/* Right side */}
      <div className="ml-auto flex items-center gap-2">
        <BackgroundSwitcher />

        {userEmail && (
          <div className="relative group">
            <button className="flex items-center gap-1.5 px-2 py-1 text-xs text-[#999] hover:text-[#e0e0e0] transition-colors duration-150 cursor-pointer bg-transparent border-none">
              <div className="w-6 h-6 rounded-full bg-[#c8956c]/20 flex items-center justify-center text-[#c8956c] text-xs font-medium">
                {userEmail.charAt(0).toUpperCase()}
              </div>
              <span className="hidden md:inline max-w-[120px] truncate">{userEmail}</span>
            </button>
            <div className="absolute right-0 top-full mt-1 w-32 liquid-glass-strong rounded-xl py-2 z-50 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150">
              <button
                onClick={onSignOut}
                className="w-full text-left px-3 py-2 text-sm text-[#999] hover:text-[#e0e0e0] transition-colors duration-150 cursor-pointer bg-transparent border-none"
              >
                Sign Out
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}
