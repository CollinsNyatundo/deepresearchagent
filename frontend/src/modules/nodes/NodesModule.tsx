import { useState, useEffect, useCallback, useMemo } from 'react'
import { toast } from 'sonner'
import {
  Plus, Search, FileText, X, Edit3, Trash2
} from 'lucide-react'
import type { Note } from '../../types/api'
import { api } from '../../api/client'
import { useResearch } from '../../lib/researchContext'
import Layout from '../../components/layout/Layout'
import NoteGraph from '../../components/notes/NoteGraph'
import { MarkdownPreview } from '../../components/notes/MarkdownPreview'

// Mock notes to use as high-fidelity seeded options or defaults if workspace is empty
const MOCKUP_DEFAULT_NOTES = [
  {
    id: 'mock-1',
    title: 'THE NIGHTGLASS CONJECTURE',
    content: 'The Nightglass neural conjecture, is confederate antas nemosoment of nearemgous connection-recolted coromares.',
    tags: ['Neural Core', 'Nightglass'],
    source: 'Theoretical Docs',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    outgoing_links: ['TEMPORAL FLUX CALCULATION', 'AETHEL SYSTEM ARCHITECTURE'],
    backlink_count: 2
  },
  {
    id: 'mock-2',
    title: 'TEMPORAL FLUX CALCULATION',
    content: 'Understanding temporal flux calculation and cotixiehremores and conoscaroing temporated ire mediates.',
    tags: ['Flux Data'],
    source: 'Time Physics',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    outgoing_links: ['NEURAL PATHWAYS'],
    backlink_count: 3
  },
  {
    id: 'mock-3',
    title: 'AETHEL SYSTEM ARCHITECTURE',
    content: 'The exact architecture of asthelare system aoechitecloral and iruver nontss ve nolisvr of murar pathways.',
    tags: ['Neural Core', 'Flux Data'],
    source: 'System Architecture',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    outgoing_links: ['THE NIGHTGLASS CONJECTURE', 'NEURAL PATHWAYS'],
    backlink_count: 1
  },
  {
    id: 'mock-4',
    title: 'NEURAL PATHWAYS',
    content: 'Neural pathways and neurab hefnosehce notes and denetrnntom watcal rosernteaf ntaresmod compreniactons for eocliatigm syetemers.',
    tags: ['Flux Data'],
    source: 'Bio Informatics',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    outgoing_links: ['AETHEL SYSTEM ARCHITECTURE'],
    backlink_count: 1
  }
]

export default function NodesModule() {
  const { selectedWorkspaceId } = useResearch()
  const [notes, setNotes] = useState<Note[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  
  // Selected Note Modal / Drawer Editor
  const [selectedNote, setSelectedNote] = useState<Note | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [editingTitle, setEditingTitle] = useState('')
  const [editingContent, setEditingContent] = useState('')

  // Fetch workspace name
  const [workspaceName, setWorkspaceName] = useState('Project Aethel')

  useEffect(() => {
    const fetchWorkspaceName = async () => {
      if (!selectedWorkspaceId) return
      try {
        const list = await api.listWorkspaces()
        const match = list.find(w => w.id === selectedWorkspaceId)
        if (match) setWorkspaceName(match.name)
      } catch (err) {
        console.error('Failed to get workspace name', err)
      }
    }
    fetchWorkspaceName()
  }, [selectedWorkspaceId])

  // Load and fetch full notes
  const fetchNotes = useCallback(async () => {
    if (!selectedWorkspaceId) {
      setNotes([])
      return
    }
    setLoading(true)
    try {
      const summaries = await api.listNotes(selectedWorkspaceId)
      if (summaries.length === 0) {
        // Fall back to MOCKUP defaults merged with empty shell
        setNotes(MOCKUP_DEFAULT_NOTES as Note[])
      } else {
        const fullNotes = await Promise.all(
          summaries.map(async (n) => {
            try {
              return await api.getNote(n.id)
            } catch {
              // Return summary wrapper if single fetch fails
              return {
                id: n.id,
                workspace_id: n.workspace_id,
                user_id: '',
                title: n.title,
                content: '',
                tags: [],
                source: null,
                created_at: n.created_at,
                updated_at: n.updated_at,
                outgoing_links: [],
                backlink_count: 0
              } as Note
            }
          })
        )
        setNotes(fullNotes)
      }
    } catch (err) {
      console.warn('Failed to fetch notes, using fallback mockup notes', err)
      setNotes(MOCKUP_DEFAULT_NOTES as Note[])
    } finally {
      setLoading(false)
    }
  }, [selectedWorkspaceId])

  useEffect(() => {
    fetchNotes()
  }, [fetchNotes])

  // Filter notes based on search query
  const filteredNotes = useMemo(() => {
    if (!searchQuery.trim()) return notes
    const q = searchQuery.toLowerCase()
    return notes.filter(
      n =>
        n.title.toLowerCase().includes(q) ||
        n.content.toLowerCase().includes(q) ||
        n.tags.some(t => t.toLowerCase().includes(q))
    )
  }, [notes, searchQuery])

  // Outgoing link map for graph component
  const graphNotesData = useMemo(() => {
    return notes.map(n => ({
      id: n.id,
      title: n.title,
      outgoing_links: n.outgoing_links || [],
      backlink_count: n.backlink_count || 0
    }))
  }, [notes])

  // Select note from graph/board click
  const selectNoteById = (id: string) => {
    const found = notes.find(n => n.id === id)
    if (found) {
      setSelectedNote(found)
      setEditingTitle(found.title)
      setEditingContent(found.content)
      setEditMode(false)
    }
  }

  // Create new note
  const handleCreateNote = async () => {
    if (!selectedWorkspaceId) {
      toast.error('Please select a project/workspace first.')
      return
    }
    try {
      const ws = await api.createNote({
        workspace_id: selectedWorkspaceId,
        title: 'New Neural Node',
        content: 'Write details here...',
      })
      toast.success('Neural node created')
      await fetchNotes()
      selectNoteById(ws.id)
      setEditMode(true)
    } catch (err) {
      toast.error('Failed to create node')
    }
  }

  // Save edited note
  const handleSaveNote = async () => {
    if (!selectedNote || selectedNote.id.startsWith('mock-')) {
      // Mock notes can't be saved, but we update client state
      if (selectedNote) {
        const updated = {
          ...selectedNote,
          title: editingTitle,
          content: editingContent
        }
        setNotes(prev => prev.map(n => n.id === selectedNote.id ? updated : n))
        setSelectedNote(updated)
      }
      setEditMode(false)
      toast.success('Seeded note mock-saved successfully!')
      return
    }
    try {
      const updated = await api.updateNote(selectedNote.id, {
        title: editingTitle,
        content: editingContent
      })
      setSelectedNote(updated)
      setEditMode(false)
      toast.success('Node updated successfully')
      fetchNotes()
    } catch (err) {
      toast.error('Failed to save node changes')
    }
  }

  // Delete note
  const handleDeleteNote = async (id: string) => {
    if (id.startsWith('mock-')) {
      setNotes(prev => prev.filter(n => n.id !== id))
      setSelectedNote(null)
      toast.success('Mock node deleted')
      return
    }
    if (!confirm('Are you sure you want to delete this neural node?')) return
    try {
      await api.deleteNote(id)
      toast.success('Node deleted')
      setSelectedNote(null)
      fetchNotes()
    } catch (err) {
      toast.error('Failed to delete node')
    }
  }

  return (
    <Layout moduleId="nodes">
      <div className="flex-1 flex overflow-hidden h-full w-full bg-transparent">
        
        {/* CENTER PANEL: Interactive Notes Board */}
        <div className="flex-1 flex flex-col min-w-0 border-r border-white/[0.06] relative h-full">
          {/* Header tabs */}
          <div className="h-11 border-b border-white/[0.06] flex items-center px-4 justify-between bg-black/20 backdrop-blur-md shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-[#c8956c] bg-[#c8956c]/[0.08] px-2 py-0.5 rounded-md border border-[#c8956c]/15">
                {workspaceName}
              </span>
              <span className="text-[#555] text-xs">/</span>
              <span className="text-xs text-[#e0e0e0] font-medium">Nodes Board</span>
            </div>
            <button
              onClick={handleCreateNote}
              className="flex items-center gap-1 text-xs text-[#c8956c] hover:text-white bg-[#c8956c]/10 hover:bg-[#c8956c]/20 px-2.5 py-1 rounded-lg transition-all cursor-pointer border-none"
            >
              <Plus className="w-3.5 h-3.5" /> New Node
            </button>
          </div>

          {/* Interactive Notes Title */}
          <div className="px-6 pt-4 shrink-0">
            <h2 className="text-sm font-semibold text-[#e0e0e0] tracking-wider uppercase font-mono">
              Interactive Notes
            </h2>
            <p className="text-xs text-[#555] mt-0.5">Click nodes to view or modify details</p>
          </div>

          {/* Canvas Board Area */}
          <div className="flex-1 overflow-auto relative p-6 select-none min-h-0">
            {loading && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-[2px] z-20">
                <div className="w-8 h-8 border-2 border-white/5 border-t-[#c8956c] rounded-full animate-spin" />
              </div>
            )}
            {/* SVG Link lines between cards */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
              <defs>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>
              {/* Curve 1 (Mock Card 1 -> Mock Card 2) */}
              <path
                d="M 320 140 C 370 140, 390 120, 480 120"
                fill="none"
                stroke="rgba(200, 149, 108, 0.3)"
                strokeWidth="1.5"
                filter="url(#glow)"
              />
              <text x="360" y="125" fill="#444" fontSize="9" className="font-mono">
                Cross-referencing
              </text>

              {/* Curve 2 (Mock Card 1 -> Mock Card 3) */}
              <path
                d="M 200 230 C 200 280, 200 320, 200 370"
                fill="none"
                stroke="rgba(200, 149, 108, 0.3)"
                strokeWidth="1.5"
                filter="url(#glow)"
              />
              <text x="210" y="300" fill="#444" fontSize="9" className="font-mono">
                Linked Data: Neural Core
              </text>

              {/* Curve 3 (Mock Card 3 -> Mock Card 2) */}
              <path
                d="M 320 420 C 370 420, 390 230, 480 180"
                fill="none"
                stroke="rgba(200, 149, 108, 0.3)"
                strokeWidth="1.5"
              />

              {/* Curve 4 (Mock Card 2 -> Mock Card 4) */}
              <path
                d="M 600 230 C 600 280, 600 320, 600 370"
                fill="none"
                stroke="rgba(200, 149, 108, 0.3)"
                strokeWidth="1.5"
                filter="url(#glow)"
              />
              <text x="610" y="300" fill="#444" fontSize="9" className="font-mono">
                Requires: Flux Data
              </text>

              {/* Curve 5 (Mock Card 3 -> Mock Card 4) */}
              <path
                d="M 320 450 C 390 450, 410 420, 480 420"
                fill="none"
                stroke="rgba(200, 149, 108, 0.3)"
                strokeWidth="1.5"
              />
            </svg>

            {/* Note Cards in relative positioning layout to match mockup */}
            <div className="relative w-full h-[600px] z-10">
              {filteredNotes.slice(0, 4).map((note, index) => {
                // Fixed coordinates corresponding to A, B, C, D in mockup
                const positions = [
                  { top: '40px', left: '40px', width: '280px' },    // Card A
                  { top: '20px', left: '480px', width: '280px' },   // Card B
                  { top: '370px', left: '40px', width: '280px' },   // Card C
                  { top: '370px', left: '480px', width: '280px' }   // Card D
                ]
                const pos = positions[index] || { top: `${index * 120}px`, left: '100px', width: '280px' }

                return (
                  <div
                    key={note.id}
                    onClick={() => selectNoteById(note.id)}
                    className="absolute liquid-glass cursor-pointer hover:-translate-y-0.5 hover:shadow-lg hover:shadow-[#c8956c]/5 border border-white/[0.06] hover:border-[#c8956c]/30 rounded-xl p-4 transition-all duration-300"
                    style={{
                      top: pos.top,
                      left: pos.left,
                      width: pos.width,
                      background: 'rgba(255, 255, 255, 0.01)',
                      backdropFilter: 'blur(8px) saturate(140%)'
                    }}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="h-1.5 w-1.5 rounded-full bg-[#c8956c] mt-1.5" />
                      <span className="text-[10px] font-mono text-[#555] select-none">
                        NODE 0{index + 1}
                      </span>
                    </div>

                    <h3 className="text-xs font-bold text-[#e0e0e0] font-mono tracking-wider mb-2">
                      {note.title}
                    </h3>
                    <p className="text-[11px] text-[#888] leading-relaxed line-clamp-3">
                      {note.content || 'Empty node description.'}
                    </p>

                    <div className="mt-4 pt-3 border-t border-white/[0.04] flex flex-wrap gap-1.5">
                      {note.tags.slice(0, 2).map((t, idx) => (
                        <span key={idx} className="text-[9px] font-mono px-2 py-0.5 rounded-md bg-white/[0.03] text-[#666]">
                          {t}
                        </span>
                      ))}
                      {note.outgoing_links?.slice(0, 1).map((link, idx) => (
                        <span key={idx} className="text-[9px] font-mono px-2 py-0.5 rounded-md bg-[#c8956c]/5 text-[#c8956c]/60">
                          Linked: {link}
                        </span>
                      ))}
                    </div>
                  </div>
                )
              })}

              {/* Excess Notes rendering if workspace contains more than 4 notes */}
              {filteredNotes.length > 4 && (
                <div className="absolute top-[520px] left-[40px] right-[40px]">
                  <p className="text-xs font-semibold text-[#555] mb-2 font-mono uppercase tracking-wider">
                    Additional Workspace Nodes ({filteredNotes.length - 4})
                  </p>
                  <div className="grid grid-cols-3 gap-4">
                    {filteredNotes.slice(4).map(note => (
                      <div
                        key={note.id}
                        onClick={() => selectNoteById(note.id)}
                        className="liquid-glass border border-white/[0.04] hover:border-[#c8956c]/30 rounded-xl p-3 cursor-pointer transition-colors"
                      >
                        <h4 className="text-xs font-semibold text-[#ccc] truncate">{note.title}</h4>
                        <p className="text-[10px] text-[#555] line-clamp-1 mt-1">{note.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT PANEL: Search Stream & Node Graph */}
        <div className="w-96 flex flex-col shrink-0 h-full">
          {/* Top Half: Search Stream */}
          <div className="flex-1 flex flex-col border-b border-white/[0.06] h-1/2 min-h-[250px] relative">
            <div className="h-11 border-b border-white/[0.06] flex items-center px-4 justify-between bg-black/20 shrink-0">
              <span className="text-xs font-semibold text-[#e0e0e0] font-mono tracking-wider">
                Search Stream
              </span>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                <span className="text-[9px] font-mono text-[#555]">LIVE STREAM</span>
              </div>
            </div>

            {/* Search Input Box */}
            <div className="p-3 border-b border-white/[0.04]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#555]" />
                <input
                  type="text"
                  placeholder='Search: "Neural synchronization"'
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="w-full text-xs bg-white/[0.02] border border-white/[0.06] focus:border-[#c8956c]/30 rounded-xl pl-9 pr-4 py-2 text-[#e0e0e0] placeholder-[#444] focus:outline-none transition-colors"
                />
              </div>
            </div>

            {/* List of active search items */}
            <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2 font-mono text-[10px]">
              <div className="p-2.5 rounded-xl border border-white/[0.04] bg-white/[0.01] flex flex-col gap-1 shrink-0">
                <div className="flex items-center justify-between text-[#555]">
                  <span>SYSTEM LOG</span>
                  <span>ACTIVE</span>
                </div>
                <p className="text-[#888] leading-relaxed">
                  Workspace indexed: <span className="text-[#c8956c]">{notes.length} nodes</span> mapped.
                </p>
              </div>

              {searchQuery.trim() && (
                <div className="p-2.5 rounded-xl border border-emerald-500/10 bg-emerald-500/[0.02] flex flex-col gap-1 shrink-0">
                  <div className="flex items-center justify-between text-[#555]">
                    <span className="text-emerald-400">QUERY EXECUTED</span>
                    <span>MATCHED</span>
                  </div>
                  <p className="text-emerald-300 leading-relaxed">
                    Found {filteredNotes.length} matching nodes for query "{searchQuery}"
                  </p>
                </div>
              )}

              {/* Matched nodes log list */}
              <div className="flex flex-col gap-1.5 mt-2 min-h-0 flex-1">
                <div className="text-[#444] uppercase tracking-wider text-[9px] font-bold px-1 mb-1">Matching Streams</div>
                <div className="flex-1 overflow-y-auto space-y-1.5 pr-0.5">
                  {filteredNotes.map(n => (
                    <button
                      key={n.id}
                      onClick={() => selectNoteById(n.id)}
                      className="w-full text-left p-2.5 rounded-xl border border-white/[0.04] hover:border-[#c8956c]/30 hover:bg-[#c8956c]/5 transition-all text-xs font-mono text-[#888] hover:text-[#e0e0e0] flex items-center justify-between cursor-pointer bg-transparent"
                    >
                      <span className="truncate max-w-[200px]">{n.title}</span>
                      <span className="text-[9px] text-[#555] shrink-0 font-bold font-mono">
                        {n.outgoing_links?.length || 0} links
                      </span>
                    </button>
                  ))}
                  {filteredNotes.length === 0 && (
                    <div className="text-[#444] text-xs p-4 text-center">No matching nodes found.</div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Half: D3 Nodes Graph */}
          <div className="flex-1 flex flex-col h-1/2 min-h-[250px] relative">
            <div className="h-10 border-b border-white/[0.04] flex items-center px-4 bg-black/10 shrink-0">
              <span className="text-[10px] font-semibold text-[#888] font-mono tracking-wider">
                Interconnected Nodes Network
              </span>
            </div>

            <div className="flex-1 relative overflow-hidden flex flex-col bg-black/10">
              {notes.length > 0 ? (
                <NoteGraph
                  notes={graphNotesData}
                  onNodeClick={selectNoteById}
                  selectedNoteId={selectedNote?.id || null}
                />
              ) : (
                <div className="flex-1 flex items-center justify-center text-[#555] text-xs">
                  Loading network graph…
                </div>
              )}
            </div>
          </div>
        </div>

        {/* MODAL / DRAWER DETAIL VIEW & WRITER */}
        {selectedNote && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-6">
            <div className="w-[640px] max-h-[85vh] flex flex-col liquid-glass border border-white/[0.08] rounded-2xl overflow-hidden bg-black/85">
              
              {/* Header */}
              <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[#c8956c]" />
                  <span className="text-sm font-semibold text-[#e0e0e0] font-mono">
                    {editMode ? 'Edit Neural Node' : 'Neural Node Details'}
                  </span>
                </div>
                <button
                  onClick={() => setSelectedNote(null)}
                  className="p-1 rounded-lg text-[#555] hover:text-[#999] transition-colors cursor-pointer border-none bg-transparent"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Scrollable details */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {editMode ? (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-[10px] font-mono uppercase tracking-wider text-[#555] mb-1.5">Title</label>
                      <input
                        type="text"
                        value={editingTitle}
                        onChange={e => setEditingTitle(e.target.value)}
                        className="w-full text-sm bg-white/[0.02] border border-white/[0.08] focus:border-[#c8956c]/30 rounded-xl px-4 py-2.5 text-[#e0e0e0] focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-mono uppercase tracking-wider text-[#555] mb-1.5">Content (Markdown)</label>
                      <textarea
                        value={editingContent}
                        onChange={e => setEditingContent(e.target.value)}
                        rows={10}
                        className="w-full text-xs font-mono bg-white/[0.02] border border-white/[0.08] focus:border-[#c8956c]/30 rounded-xl p-4 text-[#e0e0e0] focus:outline-none resize-none"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <h1 className="text-base font-bold text-[#e0e0e0] font-mono tracking-wider">{selectedNote.title}</h1>
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {selectedNote.tags.map((t, i) => (
                          <span key={i} className="text-[9px] font-mono px-2 py-0.5 rounded-md bg-white/[0.03] text-[#666]">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                    
                    <div className="pt-4 border-t border-white/[0.04] text-xs text-[#999] leading-relaxed markdown-body">
                      <MarkdownPreview
                        content={selectedNote.content || '_No content details provided._'}
                        onNavigate={(type, target) => {
                          if (type === 'note') {
                            const found = notes.find(n => n.title.toLowerCase() === target.toLowerCase())
                            if (found) selectNoteById(found.id)
                          }
                        }}
                      />
                    </div>

                    <div className="pt-4 border-t border-white/[0.04] space-y-2 text-[10px] font-mono text-[#555]">
                      <p>OUTGOING LINKS: {selectedNote.outgoing_links?.join(', ') || 'None'}</p>
                      <p>BACKLINKS COUNT: {selectedNote.backlink_count || 0}</p>
                      <p>UPDATED: {new Date(selectedNote.updated_at).toLocaleString()}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="px-5 py-4 border-t border-white/[0.06] bg-black/40 flex items-center justify-between shrink-0">
                <button
                  onClick={() => handleDeleteNote(selectedNote.id)}
                  className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 px-3 py-2 rounded-xl transition-all cursor-pointer border-none bg-transparent font-medium"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Delete Node
                </button>

                <div className="flex gap-2">
                  {editMode ? (
                    <>
                      <button
                        onClick={() => setEditMode(false)}
                        className="text-xs text-[#888] hover:text-[#bbb] bg-white/[0.03] hover:bg-white/[0.06] px-4 py-2 rounded-xl transition-all cursor-pointer border-none"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleSaveNote}
                        className="text-xs text-[#e0e0e0] hover:text-white bg-[#c8956c]/20 hover:bg-[#c8956c]/30 px-4 py-2 rounded-xl transition-all cursor-pointer border-none font-medium"
                      >
                        Save Changes
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => setEditMode(true)}
                      className="flex items-center gap-1 text-xs text-[#e0e0e0] hover:text-white bg-white/[0.05] hover:bg-white/[0.08] px-4 py-2 rounded-xl transition-all cursor-pointer border-none font-medium"
                    >
                      <Edit3 className="w-3.5 h-3.5" /> Edit Note
                    </button>
                  )}
                </div>
              </div>

            </div>
          </div>
        )}

      </div>
    </Layout>
  )
}
