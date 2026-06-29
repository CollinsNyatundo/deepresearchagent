import { Link } from 'react-router'
import { Diamond, Menu, Settings } from 'lucide-react'
import BackgroundSwitcher from '../backgrounds/BackgroundSwitcher'

interface HeaderProps {
  userEmail?: string
  onSignOut?: () => void
  /** Mobile hamburger toggle — opens the sidebar overlay on small screens */
  onToggleSidebar?: () => void
}

export default function Header({ onToggleSidebar }: HeaderProps) {
  return (
    <header className="h-[2.75rem] flex-shrink-0 liquid-glass z-10 relative flex items-center px-3 gap-3">
      {/* Mobile sidebar hamburger */}
      {onToggleSidebar && (
        <button
          onClick={onToggleSidebar}
          className="lg:hidden text-[#555] hover:text-[#e0e0e0] transition-colors cursor-pointer bg-transparent border-none p-1.5 rounded-lg hover:bg-white/[0.04]"
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

      {/* Spacer */}
      <div className="flex-1" />

      {/* Right utilities */}
      <div className="flex items-center gap-1">
        <BackgroundSwitcher />

        <Link
          to="/settings"
          className="p-1.5 rounded-lg text-[#555] hover:text-[#999] hover:bg-white/[0.04] transition-all"
          title="Settings"
        >
          <Settings className="w-4 h-4" />
        </Link>
      </div>
    </header>
  )
}
