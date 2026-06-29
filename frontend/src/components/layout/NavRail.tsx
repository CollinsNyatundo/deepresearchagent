import { Link, useLocation } from 'react-router'
import { Diamond, Telescope, BookOpen, FolderOpen, Settings, User, LogOut } from 'lucide-react'
import { cn } from '../../lib/utils'

interface NavRailProps {
  userEmail?: string
  onSignOut?: () => void
  expandedModule: string | null
  onToggleModule: (moduleId: string) => void
}

const MODULES = [
  { id: 'research',   label: 'Research',   icon: Telescope,  path: '/research'   },
  { id: 'notes',      label: 'Notes',      icon: BookOpen,   path: '/notes'      },
  { id: 'documents',  label: 'Documents',  icon: FolderOpen, path: '/documents'  },
] as const

export default function NavRail({ userEmail, onSignOut, expandedModule, onToggleModule }: NavRailProps) {
  const location = useLocation()

  const getActiveModule = () => {
    if (location.pathname.startsWith('/notes'))     return 'notes'
    if (location.pathname.startsWith('/documents')) return 'documents'
    if (location.pathname.startsWith('/settings'))  return 'settings'
    return 'research'
  }

  const activeModule = getActiveModule()

  return (
    <nav className="nav-rail h-full">
      {/* Brand mark */}
      <Link
        to="/research"
        className="flex items-center justify-center w-9 h-9 mb-4 rounded-xl hover:bg-white/[0.04] transition-colors"
        title="DeepResearch.ai"
      >
        <Diamond className="w-4 h-4 text-[#c8956c]" strokeWidth={1.5} />
      </Link>

      {/* Divider */}
      <div className="w-6 h-px bg-white/[0.06] mb-2" />

      {/* Module nav items */}
      <div className="flex flex-col gap-1 flex-1">
        {MODULES.map(({ id, label, icon: Icon, path }) => {
          const isActive = activeModule === id
          return (
            <Link
              key={id}
              to={path}
              onClick={() => onToggleModule(id)}
              className={cn('nav-rail-item', isActive && 'active')}
              aria-label={label}
            >
              <Icon className="w-4 h-4" strokeWidth={isActive ? 2 : 1.5} />
              <span className="tooltip-right">{label}</span>
            </Link>
          )
        })}

        {/* Expand/collapse toggle for sidebar panel */}
        <button
          onClick={() => onToggleModule(activeModule)}
          className={cn(
            'nav-rail-item mt-1',
            expandedModule ? 'text-[#555] hover:text-[#999]' : 'text-[#555] hover:text-[#999]'
          )}
          title={expandedModule ? 'Collapse sidebar' : 'Expand sidebar'}
          aria-label={expandedModule ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          <svg
            width="14" height="14" viewBox="0 0 14 14" fill="none"
            className={cn('transition-transform duration-300', !expandedModule && 'rotate-180')}
          >
            <path d="M9 3L5 7L9 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="tooltip-right">{expandedModule ? 'Collapse' : 'Expand'}</span>
        </button>
      </div>

      {/* Bottom utilities */}
      <div className="flex flex-col gap-1 mt-auto">
        {/* Divider */}
        <div className="w-6 h-px bg-white/[0.06] mb-2 mx-auto" />

        <Link
          to="/settings"
          className={cn('nav-rail-item', activeModule === 'settings' && 'active')}
          aria-label="Settings"
        >
          <Settings className="w-4 h-4" strokeWidth={1.5} />
          <span className="tooltip-right">Settings</span>
        </Link>

        {userEmail && (
          <div className="relative group/user">
            <button
              className="nav-rail-item"
              aria-label={userEmail}
            >
              <div className="w-6 h-6 rounded-full bg-[#c8956c]/20 flex items-center justify-center text-[#c8956c] text-[10px] font-bold">
                {userEmail.charAt(0).toUpperCase()}
              </div>
              <span className="tooltip-right">{userEmail}</span>
            </button>

            {/* Sign-out popover on hover */}
            <div className="absolute bottom-0 left-full ml-2 w-36 liquid-glass-strong rounded-xl py-2 z-50 opacity-0 invisible group-hover/user:opacity-100 group-hover/user:visible transition-all duration-150 pointer-events-none group-hover/user:pointer-events-auto">
              <div className="px-3 pb-2 pt-1 text-[10px] text-[#555] truncate border-b border-white/[0.06]">{userEmail}</div>
              <button
                onClick={onSignOut}
                className="w-full text-left px-3 py-1.5 text-xs flex items-center gap-2 text-[#999] hover:text-[#c45a5a] transition-colors cursor-pointer bg-transparent border-none"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign Out
              </button>
            </div>
          </div>
        )}

        {/* User icon fallback when no email */}
        {!userEmail && (
          <button className="nav-rail-item" aria-label="Account">
            <User className="w-4 h-4" strokeWidth={1.5} />
          </button>
        )}
      </div>
    </nav>
  )
}
