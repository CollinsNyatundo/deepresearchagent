import React, { useEffect, useState, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { useResearch } from '../../lib/researchContext'
import { useAuth } from '../../lib/authContext'
import { api } from '../../api/client'
import type { Workspace } from '../../types/api'
import { cn } from '../../lib/utils'
import {
  Moon,
  LayoutDashboard,
  Folder,
  BookOpen,
  Network,
  Calendar,
  Users,
  Bell,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Plus
} from 'lucide-react'

interface SidebarProps {
  children?: React.ReactNode
}

export default function Sidebar({ children }: SidebarProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, signOut } = useAuth()
  
  const {
    selectedWorkspaceId,
    setSelectedWorkspaceId,
    setActiveTab,
    setGlobalView
  } = useResearch()

  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [collapsed, setCollapsed] = useState(() => {
    try {
      const saved = localStorage.getItem('dra_sidebar_collapsed')
      return saved === 'true'
    } catch {
      return false
    }
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [workspaceNameInput, setWorkspaceNameInput] = useState('')
  const [showAddWorkspace, setShowAddWorkspace] = useState(false)

  // Toggle collapse state
  const toggleCollapse = () => {
    const next = !collapsed
    setCollapsed(next)
    try {
      localStorage.setItem('dra_sidebar_collapsed', String(next))
    } catch {}
  }

  // Fetch workspaces list
  const fetchWorkspaces = useCallback(async () => {
    if (!user) return
    setLoading(true)
    setError(null)
    try {
      const list = await api.listWorkspaces()
      setWorkspaces(list)
      if (list.length > 0 && !selectedWorkspaceId) {
        setSelectedWorkspaceId(list[0].id)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load workspaces'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [user, selectedWorkspaceId, setSelectedWorkspaceId])

  useEffect(() => {
    fetchWorkspaces()
  }, [user])

  // Create workspace
  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!workspaceNameInput.trim()) return
    try {
      const ws = await api.createWorkspace(workspaceNameInput.trim())
      setWorkspaceNameInput('')
      setShowAddWorkspace(false)
      await fetchWorkspaces()
      setSelectedWorkspaceId(ws.id)
    } catch (err) {
      console.error('Failed to create workspace:', err)
    }
  }

  // Navigation handlers
  const handleNav = (path: string, tab?: string) => {
    if (tab) {
      setActiveTab(tab)
    }
    if (path.startsWith('/research')) {
      setGlobalView('research')
    }
    navigate(path)
  }

  // Paths classification for active style
  const isRouteActive = (paths: string[]) => {
    return paths.some(p => location.pathname.startsWith(p))
  }

  return (
    <aside
      className={cn(
        "sidebar-container flex-shrink-0 flex flex-col h-full",
        collapsed ? "w-12" : "w-[240px]"
      )}
    >
      {/* Brand Header */}
      <div className="sidebar-brand flex items-center justify-between">
        <div className="flex items-center gap-2 overflow-hidden">
          <Moon className="w-5 h-5 text-[#c8956c] animate-pulse shrink-0" />
          {!collapsed && (
            <span className="font-semibold text-sm tracking-tight text-[#e0e0e0] font-mono">
              Nightglass <span className="text-[10px] text-[#555] font-normal">v1.4</span>
            </span>
          )}
        </div>
        {!collapsed && (
          <button
            onClick={toggleCollapse}
            className="p-1 rounded-md text-[#555] hover:text-[#999] hover:bg-white/[0.03] transition-colors cursor-pointer border-none bg-transparent"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Main Scrollable Area */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden py-3 flex flex-col gap-1.5 min-h-0">
        
        {/* Core Navigation Section */}
        <div className="px-2 flex flex-col gap-0.5">
          <button
            onClick={() => handleNav('/research', 'report')}
            className={cn(
              "sidebar-menu-item",
              isRouteActive(['/research']) && location.search.indexOf('tab=graph') === -1 && "active"
            )}
            title="Dashboard"
          >
            <LayoutDashboard className="w-4 h-4 shrink-0" />
            {!collapsed && <span>Dashboard</span>}
          </button>
          
          <button
            onClick={() => handleNav('/documents')}
            className={cn(
              "sidebar-menu-item",
              isRouteActive(['/documents']) && "active"
            )}
            title="Projects"
          >
            <Folder className="w-4 h-4 shrink-0" />
            {!collapsed && <span>Projects</span>}
          </button>

          <button
            onClick={() => handleNav('/notes')}
            className={cn(
              "sidebar-menu-item",
              isRouteActive(['/notes']) && "active"
            )}
            title="Wiki"
          >
            <BookOpen className="w-4 h-4 shrink-0" />
            {!collapsed && <span>Wiki</span>}
          </button>

          <button
            onClick={() => handleNav('/nodes')}
            className={cn(
              "sidebar-menu-item",
              isRouteActive(['/nodes']) && "active"
            )}
            title="Nodes"
          >
            <Network className="w-4 h-4 shrink-0" />
            {!collapsed && <span>Nodes</span>}
          </button>
        </div>

        {/* PROJECTS (Workspaces) Section */}
        <div className="flex flex-col gap-0.5">
          {collapsed ? (
            <div className="flex flex-col items-center py-2 mt-2 border-t border-white/[0.04]">
              <button
                type="button"
                onClick={() => {
                  toggleCollapse()
                  setTimeout(() => setShowAddWorkspace(true), 150)
                }}
                className="w-5.5 h-5.5 rounded-lg flex items-center justify-center bg-white/[0.02] hover:bg-white/[0.06] border border-white/[0.04] text-[#555] hover:text-[#999] transition-all cursor-pointer"
                title="Add Project"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="sidebar-section-title flex items-center justify-between pr-3 mt-2 border-t border-white/[0.04] pt-2">
              <span>PROJECTS</span>
              <button
                type="button"
                onClick={() => setShowAddWorkspace(!showAddWorkspace)}
                className="text-[#555] hover:text-[#999] bg-transparent border-none p-0 cursor-pointer"
                title="Add Workspace"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
          
          {!collapsed && showAddWorkspace && (
            <form onSubmit={handleCreateWorkspace} className="px-3 py-1.5 flex gap-1.5 shrink-0">
              <input
                value={workspaceNameInput}
                onChange={e => setWorkspaceNameInput(e.target.value)}
                placeholder="New project..."
                className="bg-white/[0.03] border border-white/10 rounded px-2 py-1 text-xs text-[#e0e0e0] outline-none flex-1 font-mono"
                autoFocus
              />
            </form>
          )}

          <div className="flex flex-col gap-0.5">
            {loading ? (
              !collapsed && <div className="text-[10px] text-[#444] px-4 font-mono">Loading...</div>
            ) : error ? (
              !collapsed && <div className="text-[10px] text-[#c45a5a] px-4 font-mono">Load error</div>
            ) : (
              workspaces.map(ws => {
                const isActive = selectedWorkspaceId === ws.id
                const firstLetter = ws.name.trim().charAt(0).toUpperCase() || 'P'
                return (
                  <button
                    key={ws.id}
                    onClick={() => setSelectedWorkspaceId(ws.id)}
                    className={cn(
                      "sidebar-project-item group flex items-center transition-all duration-200 border-none bg-transparent cursor-pointer w-full text-left",
                      collapsed ? "justify-center px-0" : "px-3.5 gap-2.5",
                      isActive && "active text-[#c8956c]"
                    )}
                    title={ws.name}
                  >
                    <div className={cn(
                      "w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-bold font-mono transition-all duration-200 shrink-0 select-none",
                      isActive
                        ? "bg-[#c8956c]/20 text-[#c8956c] border border-[#c8956c]/30 shadow-sm shadow-[#c8956c]/5"
                        : "bg-white/[0.02] text-[#555] border border-white/[0.04] group-hover:border-white/10 group-hover:text-[#888]"
                    )}>
                      {firstLetter}
                    </div>
                    {!collapsed && <span className="truncate text-xs font-medium tracking-wide">{ws.name}</span>}
                    {collapsed && (
                      <span className="tooltip-right">{ws.name}</span>
                    )}
                  </button>
                )
              })
            )}
          </div>
        </div>

        {/* Dynamic module specific content (RunList/NoteList/etc.) */}
        {children && !collapsed && (
          <div className="flex-1 min-h-0 flex flex-col mt-2 border-t border-white/[0.03] pt-2">
            {children}
          </div>
        )}
      </div>

      {/* Sticky Bottom Utilities */}
      <div className="sidebar-bottom">
        {collapsed ? (
          <div className="flex flex-col items-center gap-2 py-2">
            <button onClick={() => handleNav('/settings')} className="p-1.5 rounded-md text-[#555] hover:text-[#999] hover:bg-white/[0.03] transition-colors border-none bg-transparent cursor-pointer" title="Settings">
              <Settings className="w-4 h-4" />
            </button>
            <button onClick={signOut} className="p-1.5 rounded-md text-[#c45a5a] hover:text-red-400 hover:bg-white/[0.03] transition-colors border-none bg-transparent cursor-pointer" title="Sign Out">
              <LogOut className="w-4 h-4" />
            </button>
            <button
              onClick={toggleCollapse}
              className="p-1.5 rounded-md text-[#555] hover:text-[#999] hover:bg-white/[0.03] transition-colors border-none bg-transparent cursor-pointer"
              title="Expand"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <>
            <div className="sidebar-bottom-row">
              <button className="p-1.5 rounded-md text-[#555] hover:text-[#999] hover:bg-white/[0.03] transition-colors border-none bg-transparent cursor-pointer" title="Calendar (Mock)">
                <Calendar className="w-4 h-4" />
              </button>
              <button className="p-1.5 rounded-md text-[#555] hover:text-[#999] hover:bg-white/[0.03] transition-colors border-none bg-transparent cursor-pointer" title="Users (Mock)">
                <Users className="w-4 h-4" />
              </button>
              <button className="p-1.5 rounded-md text-[#555] hover:text-[#999] hover:bg-white/[0.03] transition-colors border-none bg-transparent cursor-pointer" title="Notifications (Mock)">
                <Bell className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleNav('/settings')}
                className={cn(
                  "p-1.5 rounded-md transition-colors border-none bg-transparent cursor-pointer",
                  isRouteActive(['/settings']) ? "text-[#c8956c] bg-[#c8956c]/10" : "text-[#555] hover:text-[#999] hover:bg-white/[0.03]"
                )}
                title="Settings"
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>
            
            <div className="flex items-center justify-between px-3 py-1.5 text-xs border-t border-white/[0.03] mt-1.5">
              <span className="text-[#555] truncate max-w-[140px] font-mono">{user?.email}</span>
              <button
                onClick={signOut}
                className="text-[#c45a5a] hover:text-[#e0e0e0] transition-colors duration-150 cursor-pointer bg-transparent border-none p-0 flex items-center"
                title="Sign Out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          </>
        )}
      </div>
    </aside>
  )
}
