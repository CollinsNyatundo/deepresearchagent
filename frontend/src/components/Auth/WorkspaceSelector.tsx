import React, { useEffect, useState, useCallback } from 'react'
import { api } from '../../api/client'
import { useAuth } from '../../lib/authContext'
import type { Workspace } from '../../types/api'
import { Plus, ChevronDown, RefreshCw, AlertCircle } from 'lucide-react'

type WorkspaceSelectorProps = {
  selectedWorkspaceId: string | null
  onWorkspaceSelect: (id: string | null) => void
}

export const WorkspaceSelector: React.FC<WorkspaceSelectorProps> = ({
  selectedWorkspaceId,
  onWorkspaceSelect,
}) => {
  const { user } = useAuth()
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [newWorkspaceName, setNewWorkspaceName] = useState('')
  const [loading, setLoading] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [fetchLoading, setFetchLoading] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)

  const fetchWorkspaces = useCallback(async () => {
    if (!user) return
    setFetchLoading(true)
    setFetchError(null)
    try {
      const list = await api.listWorkspaces()
      setWorkspaces(list)
      if (list.length > 0 && !selectedWorkspaceId) {
        onWorkspaceSelect(list[0].id)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load workspaces'
      setFetchError(msg)
      console.error('Failed to load workspaces', err)
    } finally {
      setFetchLoading(false)
    }
  }, [user, selectedWorkspaceId, onWorkspaceSelect])

  useEffect(() => {
    fetchWorkspaces()
  }, [user])

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newWorkspaceName.trim()) return
    setLoading(true)
    setCreateError(null)
    try {
      const created = await api.createWorkspace(newWorkspaceName)
      setNewWorkspaceName('')
      setCreateModalOpen(false)
      await fetchWorkspaces()
      onWorkspaceSelect(created.id)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to create workspace'
      setCreateError(msg)
      console.error('Failed to create workspace', err)
    } finally {
      setLoading(false)
    }
  }

  const selectedWorkspace = workspaces.find((ws) => ws.id === selectedWorkspaceId)

  return (
    <div className="relative flex flex-col gap-1.5">
      {/* Error banner with retry */}
      {fetchError && (
        <div className="flex items-start gap-2 px-2 py-1.5 rounded-lg bg-[#c45a5a]/10 border border-[#c45a5a]/20 text-[10px] text-[#e07070]">
          <AlertCircle className="w-3 h-3 shrink-0 mt-0.5" />
          <span className="flex-1 leading-tight">Workspace load failed. Select a workspace to unlock buttons.</span>
          <button
            onClick={fetchWorkspaces}
            disabled={fetchLoading}
            className="flex items-center gap-1 shrink-0 underline underline-offset-2 text-[#e07070] hover:text-[#e0e0e0] cursor-pointer bg-transparent border-none p-0 disabled:opacity-50"
            title="Retry"
          >
            <RefreshCw className={`w-3 h-3 ${fetchLoading ? 'animate-spin' : ''}`} />
            Retry
          </button>
        </div>
      )}

      <div className="flex items-center gap-2">
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          disabled={fetchLoading}
          className="flex items-center gap-2 px-3 py-2 bg-white/[0.05] border border-white/10 rounded-xl text-sm text-[#e0e0e0] hover:bg-white/[0.08] transition-colors duration-150 cursor-pointer min-w-[180px] disabled:opacity-60 disabled:cursor-wait"
        >
          {fetchLoading ? (
            <span className="flex items-center gap-2 flex-1 text-left text-[#aaa]">
              <RefreshCw className="w-3 h-3 animate-spin" />
              Loading…
            </span>
          ) : (
            <span className={`truncate flex-1 text-left ${selectedWorkspace ? 'text-[#e0e0e0]' : 'text-[#bbb]'}`}>
              {selectedWorkspace?.name ?? 'Select workspace'}
            </span>
          )}
          <ChevronDown className="w-4 h-4 text-[#aaa] shrink-0" />
        </button>
        <button
          onClick={() => { setCreateModalOpen(true); setCreateError(null) }}
          className="p-2 rounded-xl bg-white/[0.05] border border-white/10 text-[#bbb] hover:text-[#e0e0e0] hover:bg-white/[0.08] transition-colors duration-150 cursor-pointer"
          title="New Workspace"
        >
          <Plus className="w-4 h-4" />
        </button>

      </div>

      {dropdownOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setDropdownOpen(false)} />
          <div className="absolute top-full left-0 mt-1 w-full min-w-[220px] liquid-glass-strong rounded-xl py-2 z-50 shadow-2xl">
            {workspaces.length === 0 ? (
              <div className="px-3 py-2 text-sm text-[#aaa]">No workspaces — create one →</div>
            ) : (
              workspaces.map((ws) => (
                <button
                  key={ws.id}
                  onClick={() => {
                    onWorkspaceSelect(ws.id)
                    setDropdownOpen(false)
                  }}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors duration-150 cursor-pointer border-none bg-transparent ${
                    ws.id === selectedWorkspaceId
                      ? 'text-[#c8956c]'
                      : 'text-[#d0d0d0] hover:text-white hover:bg-white/[0.05]'
                  }`}
                >
                  {ws.name}
                </button>
              ))
            )}
          </div>
        </>
      )}

      {/* Create Workspace Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60" onClick={() => setCreateModalOpen(false)} />
          <div className="relative w-full max-w-sm mx-4 liquid-glass-strong rounded-2xl p-6">
            <h3 className="text-lg font-bold text-[#e0e0e0] mb-4">Create Workspace</h3>
            <form onSubmit={handleCreateWorkspace} className="space-y-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#bbb] font-semibold mb-2">Workspace Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Research Team"
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  disabled={loading}
                  className="w-full bg-white/[0.06] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-[#e0e0e0] placeholder:text-[#888] focus:outline-none focus:border-[#c8956c]/50 disabled:opacity-50"
                />
              </div>
              {createError && (
                <div className="flex items-center gap-2 text-xs text-[#e07070] bg-[#c45a5a]/10 border border-[#c45a5a]/20 rounded-lg px-3 py-2">
                  <AlertCircle className="w-3 h-3 shrink-0" />
                  {createError}
                </div>
              )}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 px-4 rounded-xl text-sm font-medium bg-[#c8956c]/15 text-[#c8956c] hover:bg-[#c8956c]/25 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150 cursor-pointer border-none"
              >
                {loading ? 'Creating...' : 'Create'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
