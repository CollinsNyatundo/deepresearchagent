import React, { useEffect, useState, useRef, useCallback, useMemo, Suspense } from 'react'
import { toast } from 'sonner'
import { useNavigate, useSearchParams } from 'react-router'
import {
  Plus, Search, FileText, X, Edit3, Eye as PreviewIcon,
  ArrowLeft, Network, Trash2, Sparkles, Loader2
} from 'lucide-react'
import type { Note, NoteSummary, Backlink } from '../../types/api'
import { api } from '../../api/client'
import { useAuth } from '../../lib/authContext'
import { WorkspaceSelector } from '../../components/Auth/WorkspaceSelector'
import Layout from '../../components/layout/Layout'
import { MarkdownPreview } from '../../components/notes/MarkdownPreview'
import MoonPhaseWidget from '../../components/notes/MoonPhaseWidget'
import { useVirtualList } from '../../hooks/useVirtualList'

export default function NotesModule() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null)
  const [notes, setNotes] = useState<NoteSummary[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedNote, setSelectedNote] = useState<Note | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [viewMode, setViewMode] = useState<'editor' | 'graph'>('editor')
  const NoteGraph = useMemo(() => React.lazy(() => import('../../components/notes/NoteGraph')), [])
  const [manageMode, setManageMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [backlinks, setBacklinks] = useState<Backlink[]>([])
  const [saving, setSaving] = useState(false)
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')

  // Module memory: persist view mode
  useEffect(() => {
    const saved = localStorage.getItem('notes_view_mode')
    if (saved === 'graph' || saved === 'editor') {
      setViewMode(saved)
    }
  }, [])

  useEffect(() => {
    localStorage.setItem('notes_view_mode', viewMode)
  }, [viewMode])

  // Editor state
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [source, setSource] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [graphNotes, setGraphNotes] = useState<Note[]>([])
  const [graphLoading, setGraphLoading] = useState(false)
  const [seeding, setSeeding] = useState(false)

  const {
    containerRef: notesContainerRef,
    visibleItems: visibleNotes,
    totalHeight: notesTotalHeight,
    offsetY: notesOffsetY,
    onScroll: onNotesScroll,
  } = useVirtualList(notes, { itemHeight: 40 })

  const handleSeedNotes = async () => {
    if (!selectedWorkspaceId) return
    setSeeding(true)
    try {
      const res = await api.seedNotes(selectedWorkspaceId)
      if (res.success) {
        fetchNotes()
        toast.success(res.message)
      } else {
        toast.error(res.message)
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to seed notes')
    } finally { setSeeding(false) }
  }

  const handleResearchThisTopic = async () => {
    if (!selectedWorkspaceId || !selectedNote) return
    try {
      const res = await api.createResearchRun({
        workspace_id: selectedWorkspaceId,
        query: `Research: ${title || selectedNote.title}`,
        mode: 'web',
        depth: 3,
      })
      navigate(`/research?run=${res.run_id}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to start research')
    }
  }

  const fetchGraphNotes = useCallback(async () => {
    if (!selectedWorkspaceId) { setGraphNotes([]); return }
    setGraphLoading(true)
    try {
      const list = await api.listNotes(selectedWorkspaceId)
      const full = await Promise.all(list.map(n => api.getNote(n.id)))
      setGraphNotes(full)
    } catch (err) {
      console.error('Failed to load graph notes:', err)
    } finally { setGraphLoading(false) }
  }, [selectedWorkspaceId])

  useEffect(() => {
    if (viewMode === 'graph' && graphNotes.length === 0) {
      fetchGraphNotes()
    }
  }, [viewMode, graphNotes.length, fetchGraphNotes])

  const fetchNotes = useCallback(async () => {
    if (!selectedWorkspaceId) { setNotes([]); return }
    setLoading(true)
    try {
      if (searchQuery.trim()) {
        const res = await api.searchNotes(selectedWorkspaceId, searchQuery)
        setNotes(res.notes)
      } else {
        const list = await api.listNotes(selectedWorkspaceId)
        setNotes(list)
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load notes')
    } finally { setLoading(false) }
  }, [selectedWorkspaceId, searchQuery])

  useEffect(() => { fetchNotes() }, [fetchNotes])

  // Handle cross-module navigation query params
  useEffect(() => {
    const noteTitle = searchParams.get('note')
    if (noteTitle && notes.length > 0) {
      const found = notes.find(n => n.title.toLowerCase() === noteTitle.toLowerCase())
      if (found) { loadNote(found.id) }
    }
  }, [searchParams, notes])

  const loadNote = async (id: string) => {
    try {
      const note = await api.getNote(id)
      setSelectedNote(note)
      setTitle(note.title)
      setContent(note.content)
      setSource(note.source || '')
      setTags(note.tags || [])
      setEditMode(false)
      const bl = await api.getNoteBacklinks(id)
      setBacklinks(bl)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load note')
    }
  }

  const saveNote = async () => {
    if (!selectedNote || !selectedWorkspaceId) return
    setSaving(true)
    try {
      const updated = await api.updateNote(selectedNote.id, {
        title, content, tags, source: source || undefined
      })
      setSelectedNote(updated)
      fetchNotes()
      toast.success('Note saved')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save')
    } finally { setSaving(false) }
  }

  const createNote = async () => {
    if (!selectedWorkspaceId) { toast.error('Select a workspace first'); return }
    try {
      const note = await api.createNote({
        workspace_id: selectedWorkspaceId,
        title: 'Untitled Note',
        content: '',
        tags: [],
      })
      setSelectedNote(note)
      setTitle(note.title)
      setContent(note.content)
      setTags(note.tags)
      setSource('')
      setEditMode(true)
      fetchNotes()
      toast.success('Note created')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create note')
    }
  }

  const deleteSelected = async () => {
    if (!selectedIds.size) return
    if (!confirm(`Delete ${selectedIds.size} note(s)?`)) return
    try {
      await api.deleteNotesBulk(Array.from(selectedIds))
      setSelectedIds(new Set())
      setManageMode(false)
      fetchNotes()
      if (selectedNote && selectedIds.has(selectedNote.id)) {
        setSelectedNote(null)
      }
      toast.success('Notes deleted')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete')
    }
  }

  const handleWikiNavigate = (type: string, target: string) => {
    if (type === 'note') {
      const found = notes.find(n => n.title.toLowerCase() === target.toLowerCase())
      if (found) { loadNote(found.id) }
      else if (confirm(`Note "${target}" doesn't exist. Create it?`)) {
        createNote().then(() => {
          setTitle(target)
          setContent(`# ${target}\n\n`)
          setEditMode(true)
        })
      }
    } else if (type === 'run') {
      navigate(`/research?run=${target}`)
    } else if (type === 'doc') {
      navigate(`/documents?doc=${target}`)
    } else if (type === 'wiki') {
      navigate(`/documents?wiki=${encodeURIComponent(target)}`)
    }
  }

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const addTag = () => {
    if (!tagInput.trim() || tags.includes(tagInput.trim())) return
    setTags([...tags, tagInput.trim()])
    setTagInput('')
  }

  const removeTag = (tag: string) => setTags(tags.filter(t => t !== tag))

  // Auto-save debounce
  useEffect(() => {
    if (!selectedNote || !editMode) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      saveNote()
    }, 400)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [title, content, tags, source])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault()
        if (selectedNote && editMode) saveNote()
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'n' && !e.shiftKey) {
        e.preventDefault()
        createNote()
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'e') {
        e.preventDefault()
        if (selectedNote) setViewMode(viewMode === 'editor' ? 'graph' : 'editor')
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        const searchInput = document.querySelector('input[placeholder*="Search notes"]') as HTMLInputElement
        searchInput?.focus()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [selectedNote, editMode, viewMode, title, content, tags, source])

  const sidebarContent = (
    <div className="flex flex-col h-full p-3 gap-3">
      <WorkspaceSelector selectedWorkspaceId={selectedWorkspaceId} onWorkspaceSelect={setSelectedWorkspaceId} />

      <button
        onClick={createNote}
        className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl text-sm font-medium text-[#e0e0e0] bg-[#c8956c]/15 hover:bg-[#c8956c]/25 transition-colors duration-150 cursor-pointer border-none"
      >
        <Plus className="w-4 h-4" />
        New Note
      </button>

      {!loading && notes.length === 0 && (
        <button
          onClick={handleSeedNotes}
          disabled={seeding}
          className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl text-sm font-medium text-[#e0e0e0] bg-white/[0.05] hover:bg-white/[0.08] transition-colors duration-150 cursor-pointer border-none disabled:opacity-50"
        >
          {seeding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          Seed Starter Notes
        </button>
      )}

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#555]" />
        <input
          type="text" placeholder="Search notes..."
          value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
          className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl pl-9 pr-3 py-2 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:outline-none focus:border-[#c8956c]/50"
        />
      </div>

      <div className="flex items-center justify-between px-1">
        <span className="text-[10px] uppercase tracking-wider text-[#555] font-semibold">Notes</span>
        <button
          onClick={() => { setManageMode(!manageMode); setSelectedIds(new Set()) }}
          className={`text-[10px] uppercase tracking-wider font-semibold transition-colors duration-150 cursor-pointer bg-transparent border-none ${manageMode ? 'text-[#c8956c]' : 'text-[#555] hover:text-[#999]'}`}
        >
          {manageMode ? 'Done' : 'Manage'}
        </button>
      </div>

      {manageMode && selectedIds.size > 0 && (
        <button
          onClick={deleteSelected}
          className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-xl text-xs font-medium bg-[#c45a5a]/10 text-[#c45a5a] hover:bg-[#c45a5a]/20 transition-colors duration-150 cursor-pointer border-none"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Delete {selectedIds.size}
        </button>
      )}

      <div ref={notesContainerRef} onScroll={onNotesScroll} className="flex-1 overflow-y-auto min-h-0">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 border-2 border-[#333] border-t-[#c8956c] rounded-full animate-spin" />
          </div>
        ) : notes.length === 0 ? (
          <div className="flex flex-col items-center py-8 gap-2 text-center">
            <FileText className="w-8 h-8 text-[#333]" />
            <span className="text-sm text-[#555]">No notes yet.</span>
            <span className="text-xs text-[#555]">Click "New Note" to get started.</span>
          </div>
        ) : (
          <div style={{ height: notesTotalHeight, position: 'relative' }}>
            <div style={{ transform: `translateY(${notesOffsetY}px)` }} className="flex flex-col gap-1">
              {visibleNotes.map((note) => (
                <div
                  key={note.id}
                  className={`flex items-center gap-2 px-2 py-2 rounded-xl transition-all duration-150 ${
                    selectedNote?.id === note.id ? 'bg-white/[0.06]' : 'hover:bg-white/[0.03]'
                  }`}
                >
                  {manageMode && (
                    <input
                      type="checkbox"
                      checked={selectedIds.has(note.id)}
                      onChange={() => toggleSelect(note.id)}
                      className="w-4 h-4 accent-[#c8956c] cursor-pointer"
                    />
                  )}
                  <button
                    onClick={() => loadNote(note.id)}
                    className="flex-1 text-left text-sm truncate cursor-pointer bg-transparent border-none text-[#999] hover:text-[#e0e0e0]"
                  >
                    {note.title || 'Untitled'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="mt-auto pt-3 border-t border-white/[0.06] flex flex-col gap-2">
        <div className="flex items-center gap-2 px-1">
          <MoonPhaseWidget size={24} />
          <span className="text-[10px] text-[#555]">Moon Phase</span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-[#555] truncate max-w-[140px]">{user?.email}</span>
          <button onClick={signOut} className="text-xs text-[#c45a5a] hover:text-[#e0e0e0] transition-colors duration-150 cursor-pointer bg-transparent border-none">Sign Out</button>
        </div>
      </div>
    </div>
  )

  const mainContent = (
    <div className="flex-1 overflow-hidden flex flex-col">
      {!selectedNote ? (
        <div className="flex-1 flex items-center justify-center text-[#555]">
          <div className="text-center space-y-4">
            <FileText className="w-12 h-12 mx-auto text-[#333]" />
            <h2 className="text-xl font-semibold text-[#e0e0e0]">Your Notes</h2>
            <p className="text-sm max-w-md">Select a note from the sidebar or create a new one. Use [[Wiki Links]] to connect notes together.</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-hidden flex flex-col">
          {/* Toolbar */}
          <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.06]">
            <div className="flex items-center gap-2">
              <button onClick={() => setSelectedNote(null)} className="p-1.5 rounded-lg text-[#555] hover:text-[#999] hover:bg-white/[0.03] cursor-pointer border-none">
                <ArrowLeft className="w-4 h-4" />
              </button>
              <div className="flex bg-white/[0.03] rounded-xl p-0.5">
                {([
                  { id: 'editor' as const, label: 'Editor', icon: Edit3 },
                  { id: 'graph' as const, label: 'Graph', icon: Network },
                ]).map(t => (
                  <button key={t.id} onClick={() => setViewMode(t.id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-150 cursor-pointer border-none ${
                      viewMode === t.id ? 'bg-white/[0.06] text-[#e0e0e0]' : 'text-[#555] hover:text-[#999]'
                    }`}>
                    <t.icon className="w-3.5 h-3.5" />
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {viewMode === 'editor' && (
                <div className="flex bg-white/[0.03] rounded-xl p-0.5">
                  <button onClick={() => setEditMode(true)}
                    className={`px-3 py-1.5 text-xs rounded-lg transition-all duration-150 cursor-pointer border-none ${editMode ? 'bg-white/[0.06] text-[#e0e0e0]' : 'text-[#555] hover:text-[#999]'}`}>
                    <Edit3 className="w-3.5 h-3.5 inline mr-1" />
                    Edit
                  </button>
                  <button onClick={() => { setEditMode(false); saveNote() }}
                    className={`px-3 py-1.5 text-xs rounded-lg transition-all duration-150 cursor-pointer border-none ${!editMode ? 'bg-white/[0.06] text-[#e0e0e0]' : 'text-[#555] hover:text-[#999]'}`}>
                    <PreviewIcon className="w-3.5 h-3.5 inline mr-1" />
                    Preview
                  </button>
                </div>
              )}
              <button
                onClick={handleResearchThisTopic}
                className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs bg-[#c8956c]/15 text-[#c8956c] hover:bg-[#c8956c]/25 transition-colors cursor-pointer border-none"
                title="Research this topic"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Research
              </button>
              {saving && <span className="text-xs text-[#555]">Saving...</span>}
              <button onClick={() => { setSelectedNote(null); fetchNotes() }}
                className="p-1.5 rounded-lg text-[#555] hover:text-[#c45a5a] hover:bg-[#c45a5a]/10 cursor-pointer border-none" title="Close">
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Content */}
          {viewMode === 'editor' ? (
            <div className="flex-1 overflow-hidden flex">
              <div className="flex-1 overflow-y-auto p-4">
                {editMode ? (
                  <div className="max-w-[42rem] mx-auto space-y-4">
                    <input
                      type="text" value={title} onChange={e => setTitle(e.target.value)}
                      placeholder="Note title..."
                      className="w-full bg-transparent border-none text-xl font-semibold text-[#e0e0e0] placeholder:text-[#555] focus:outline-none focus:ring-0"
                    />
                    <div className="flex items-center gap-2 flex-wrap">
                      {tags.map(tag => (
                        <span key={tag} className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] rounded-full bg-[#c8956c]/10 text-[#c8956c] border border-[#c8956c]/20">
                          {tag}
                          <button onClick={() => removeTag(tag)} className="cursor-pointer bg-transparent border-none text-[#c8956c] hover:text-[#e0e0e0]"><X className="w-3 h-3" /></button>
                        </span>
                      ))}
                      <div className="flex items-center gap-1">
                        <input
                          type="text" value={tagInput} onChange={e => setTagInput(e.target.value)}
                          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag() } }}
                          placeholder="Add tag..."
                          className="w-24 bg-white/[0.03] border border-white/[0.06] rounded-lg px-2 py-1 text-[10px] text-[#e0e0e0] placeholder:text-[#555] focus:outline-none focus:border-[#c8956c]/50"
                        />
                      </div>
                    </div>
                    <textarea
                      value={content} onChange={e => setContent(e.target.value)}
                      placeholder="Write your note here... Use [[Wiki Links]] to connect notes."
                      className="w-full flex-1 bg-transparent border-none text-sm text-[#bbb] placeholder:text-[#555] font-mono leading-relaxed resize-none focus:outline-none focus:ring-0 min-h-[60vh]"
                    />
                    <input
                      type="text" value={source} onChange={e => setSource(e.target.value)}
                      placeholder="Source (optional)"
                      className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 text-xs text-[#999] placeholder:text-[#555] focus:outline-none focus:border-[#c8956c]/50"
                    />
                  </div>
                ) : (
                  <div className="max-w-[42rem] mx-auto">
                    <h1 className="text-2xl font-semibold text-[#e0e0e0] mb-2">{title || 'Untitled'}</h1>
                    {tags.length > 0 && (
                      <div className="flex items-center gap-1.5 mb-4 flex-wrap">
                        {tags.map(tag => (
                          <span key={tag} className="px-2 py-0.5 text-[10px] rounded-full bg-[#c8956c]/10 text-[#c8956c] border border-[#c8956c]/20">{tag}</span>
                        ))}
                      </div>
                    )}
                    <MarkdownPreview content={content} onNavigate={handleWikiNavigate} />
                    {source && (
                      <div className="mt-6 pt-4 border-t border-white/[0.06] text-xs text-[#555]">
                        Source: {source}
                      </div>
                    )}

                    {/* Backlinks */}
                    {backlinks.length > 0 && (
                      <div className="mt-6 pt-4 border-t border-white/[0.06]">
                        <h3 className="text-xs uppercase tracking-wider text-[#555] font-semibold mb-2">Linked from ({backlinks.length})</h3>
                        <div className="flex flex-col gap-1">
                          {backlinks.map(bl => (
                            <button key={bl.id} onClick={() => loadNote(bl.id)}
                              className="text-left text-sm text-[#999] hover:text-[#c8956c] transition-colors duration-150 cursor-pointer bg-transparent border-none truncate">
                              ← {bl.title}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Outgoing links */}
                    {selectedNote.outgoing_links.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-white/[0.06]">
                        <h3 className="text-xs uppercase tracking-wider text-[#555] font-semibold mb-2">Links to ({selectedNote.outgoing_links.length})</h3>
                        <div className="flex flex-col gap-1">
                          {selectedNote.outgoing_links.map((link, i) => (
                            <span key={i} className="text-sm text-[#d4a574] cursor-pointer hover:text-[#c8956c] hover:underline"
                              onClick={() => handleWikiNavigate('note', link)}>
                              → {link}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <Suspense fallback={<div className="flex-1 flex items-center justify-center"><div className="w-8 h-8 border-2 border-[#333] border-t-[#c8956c] rounded-full animate-spin" /></div>}>
              {graphLoading ? (
                <div className="flex-1 flex items-center justify-center">
                  <div className="w-8 h-8 border-2 border-[#333] border-t-[#c8956c] rounded-full animate-spin" />
                </div>
              ) : (
                <NoteGraph notes={graphNotes} onNodeClick={loadNote} selectedNoteId={selectedNote?.id || null} />
              )}
            </Suspense>
          )}
        </div>
      )}
    </div>
  )

  return (
    <Layout sidebar={sidebarContent} userEmail={user?.email} onSignOut={signOut}>
      {mainContent}
    </Layout>
  )
}
