import { toast } from 'sonner'
import { useState, useCallback, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import {
  Upload, File, Search, MessageSquare, BookOpen, Wrench,
  X, Send, Loader2, ChevronRight, Sparkles, Trash2, Download, RefreshCw, BookCopy,
  FolderOpen, CheckCircle, RotateCcw, AlertTriangle, FlaskConical
} from 'lucide-react'
import type { Document, WikiPage } from '../../types/api'
import { api } from '../../api/client'
import { useAuth } from '../../lib/authContext'
import { useResearch } from '../../lib/researchContext'
import Layout from '../../components/layout/Layout'
import { MarkdownPreview } from '../../components/notes/MarkdownPreview'

export default function DocumentsModule() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { selectedWorkspaceId } = useResearch()
  const [searchQuery, setSearchQuery] = useState('')
  const [activeDocTab, setActiveDocTab] = useState<'upload' | 'query' | 'chat' | 'wiki' | 'skills'>('upload')
  const [documents, setDocuments] = useState<Document[]>([])
  const [wikiPages, setWikiPages] = useState<WikiPage[]>([])

  // Module memory: persist active tab
  useEffect(() => {
    const saved = localStorage.getItem('documents_active_tab')
    if (saved) {
      const validTabs = ['upload', 'query', 'chat', 'wiki', 'skills'] as const
      if (validTabs.includes(saved as typeof validTabs[number])) {
        setActiveDocTab(saved as typeof validTabs[number])
      }
    }
  }, [])

  useEffect(() => {
    localStorage.setItem('documents_active_tab', activeDocTab)
  }, [activeDocTab])
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Query state
  const [question, setQuestion] = useState('')
  const [queryAnswer, setQueryAnswer] = useState('')
  const [queryLoading, setQueryLoading] = useState(false)
  const [querySaving, setQuerySaving] = useState(false)

  // Chat state
  const [chatMessages, setChatMessages] = useState<{role: string; content: string}[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatSessionId, setChatSessionId] = useState<string>('')
  const chatEndRef = useRef<HTMLDivElement>(null)

  const handleChat = async () => {
    if (!chatInput.trim() || !selectedWorkspaceId || chatLoading) return
    const msg = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', content: msg }])
    setChatLoading(true)
    try {
      const res = await api.chatDocuments(selectedWorkspaceId, msg, chatSessionId || undefined)
      setChatSessionId(res.session_id)
      setChatMessages(res.history)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Chat failed')
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }])
    } finally { setChatLoading(false) }
  }

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const handleSaveQueryToNotes = async () => {
    if (!selectedWorkspaceId || !queryAnswer) return
    setQuerySaving(true)
    try {
      const noteTitle = `Query: ${question.substring(0, 50)}${question.length > 50 ? '...' : ''}`
      const noteContent = `${queryAnswer}\n\n---\n\n*Question: ${question}*`
      await api.createNote({
        workspace_id: selectedWorkspaceId,
        title: noteTitle,
        content: noteContent,
        tags: ['document-query'],
        source: '',
      })
      toast.success('Saved to Notes')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Save failed')
    } finally { setQuerySaving(false) }
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        const searchInput = document.querySelector('input[placeholder*="Search documents"]') as HTMLInputElement
        searchInput?.focus()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [])

  // Wiki state
  const [selectedWikiPage, setSelectedWikiPage] = useState<string | null>(null)
  const [wikiContent, setWikiContent] = useState('')
  const [wikiLoading, setWikiLoading] = useState(false)

  // Skill state
  const [skillName, setSkillName] = useState('')
  const [skillIntent, setSkillIntent] = useState('')
  const [skillLoading, setSkillLoading] = useState(false)
  const [skillResult, setSkillResult] = useState('')
  const [skillsList, setSkillsList] = useState<string[]>([])
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null)
  const [skillActionLoading, setSkillActionLoading] = useState<'validate' | 'eval' | 'rollback' | null>(null)
  const [skillActionResult, setSkillActionResult] = useState<string | null>(null)

  // Query history per workspace (localStorage)
  const [queryHistory, setQueryHistory] = useState<{ question: string; answer: string; timestamp: string }[]>([])
  const [showHistory, setShowHistory] = useState(false)

  useEffect(() => {
    if (!selectedWorkspaceId) return
    const saved = localStorage.getItem(`doc_query_history_${selectedWorkspaceId}`)
    if (saved) {
      try { setQueryHistory(JSON.parse(saved)) } catch { /* ignore */ }
    } else {
      setQueryHistory([])
    }
  }, [selectedWorkspaceId])

  const saveToHistory = useCallback((question: string, answer: string) => {
    if (!selectedWorkspaceId) return
    setQueryHistory(prev => {
      const next = [{ question, answer, timestamp: new Date().toISOString() }, ...prev].slice(0, 50)
      localStorage.setItem(`doc_query_history_${selectedWorkspaceId}`, JSON.stringify(next))
      return next
    })
  }, [selectedWorkspaceId])

  const handleDeleteHistoryItem = (index: number) => {
    setQueryHistory(prev => {
      const next = prev.filter((_, i) => i !== index)
      if (selectedWorkspaceId) {
        localStorage.setItem(`doc_query_history_${selectedWorkspaceId}`, JSON.stringify(next))
      }
      return next
    })
  }

  // Stats state
  const [stats, setStats] = useState<{
    document_count: number;
    concept_count: number;
    entity_count: number;
    summary_count: number;
    wiki_size_bytes: number;
  } | null>(null)
  const [recompiling, setRecompiling] = useState(false)
  const [researchGapsLoading, setResearchGapsLoading] = useState(false)

  const handleResearchGaps = async () => {
    if (!selectedWorkspaceId) return
    setResearchGapsLoading(true)
    try {
      const res = await api.createResearchRun({
        workspace_id: selectedWorkspaceId,
        query: `Identify and research gaps in the document collection for workspace ${selectedWorkspaceId}. What topics are missing or underrepresented?`,
        mode: 'web',
        depth: 3,
      })
      navigate(`/research?run=${res.run_id}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to research gaps')
    } finally { setResearchGapsLoading(false) }
  }

  const handleSkillAction = async (action: 'validate' | 'eval' | 'rollback') => {
    if (!selectedWorkspaceId || !selectedSkill) return
    setSkillActionLoading(action)
    setSkillActionResult(null)
    try {
      if (action === 'validate') {
        const res = await api.validateSkill(selectedWorkspaceId, selectedSkill)
        setSkillActionResult(res.valid
          ? `✓ ${selectedSkill} validated. Files: ${res.files?.join(', ') || 'N/A'}`
          : `✗ Validation failed: ${res.error}`)
      } else if (action === 'eval') {
        const res = await api.evaluateSkill(selectedWorkspaceId, selectedSkill)
        setSkillActionResult(res.error
          ? `✗ Evaluation failed: ${res.error}`
          : `✓ ${selectedSkill} coverage: ${res.coverage}% (${res.concepts_matched}/${res.total_concepts} concepts matched)`)
      } else if (action === 'rollback') {
        const res = await api.rollbackSkill(selectedWorkspaceId, selectedSkill)
        setSkillActionResult(res.success
          ? `✓ ${res.message}`
          : `✗ Rollback failed: ${res.error}`)
      }
    } catch (err) {
      setSkillActionResult(err instanceof Error ? err.message : 'Action failed')
    } finally { setSkillActionLoading(null) }
  }

  const handleWikiNavigate = (type: string, target: string) => {
    if (type === 'note') {
      navigate(`/notes?note=${encodeURIComponent(target)}`)
    } else if (type === 'run') {
      navigate(`/research?run=${target}`)
    } else if (type === 'doc') {
      setActiveDocTab('upload')
      const found = documents.find(d => d.filename.toLowerCase().includes(target.toLowerCase()))
      if (found) {
        // Scroll to or highlight the document in the list
      }
    } else if (type === 'wiki') {
      setActiveDocTab('wiki')
      const found = wikiPages.find(p => p.title.toLowerCase() === target.toLowerCase())
      if (found) { loadWikiPage(found.path) }
    }
  }

  const fetchDocuments = useCallback(async () => {
    if (!selectedWorkspaceId) { setDocuments([]); setWikiPages([]); return }
    try {
      const res = await api.listDocuments(selectedWorkspaceId)
      setDocuments(res.documents)
      setWikiPages(res.wiki_pages)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load documents')
    }
  }, [selectedWorkspaceId])

  useEffect(() => { fetchDocuments() }, [fetchDocuments])

  const fetchStats = useCallback(async () => {
    if (!selectedWorkspaceId) return
    try {
      const res = await api.getDocumentStats(selectedWorkspaceId)
      setStats(res)
    } catch (err) {
      console.error('Failed to load stats:', err)
    }
  }, [selectedWorkspaceId])

  useEffect(() => { fetchStats() }, [fetchStats])

  const handleDeleteDocument = async (docId: string) => {
    if (!selectedWorkspaceId) return
    if (!confirm('Delete this document?')) return
    try {
      await api.deleteDocument(selectedWorkspaceId, docId)
      fetchDocuments()
      fetchStats()
      toast.success('Document deleted')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  const handleRecompile = async () => {
    if (!selectedWorkspaceId) return
    setRecompiling(true)
    try {
      await api.recompileDocuments(selectedWorkspaceId)
      fetchDocuments()
      fetchStats()
      toast.success('Documents recompiled')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Recompile failed')
    } finally { setRecompiling(false) }
  }

  // Handle cross-module navigation query params
  useEffect(() => {
    const wiki = searchParams.get('wiki')
    const doc = searchParams.get('doc')
    if (wiki) {
      setActiveDocTab('wiki')
      const found = wikiPages.find(p => p.title.toLowerCase() === wiki.toLowerCase())
      if (found) { loadWikiPage(found.path) }
    } else if (doc) {
      setActiveDocTab('upload')
    }
  }, [searchParams, wikiPages])

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || !selectedWorkspaceId) return
    setUploading(true)
    setUploadProgress(0)
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        await api.uploadDocument(selectedWorkspaceId, file)
        setUploadProgress(Math.round(((i + 1) / files.length) * 100))
      }
      fetchDocuments()
      toast.success(`${files.length} document(s) uploaded`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Upload failed')
    } finally { setUploading(false); setUploadProgress(0) }
  }

  const handleQuery = async () => {
    if (!question.trim() || !selectedWorkspaceId) return
    setQueryLoading(true)
    try {
      const res = await api.queryDocuments(selectedWorkspaceId, question.trim())
      setQueryAnswer(res.answer)
      saveToHistory(question.trim(), res.answer)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Query failed')
    } finally { setQueryLoading(false) }
  }

  const loadWikiPage = async (path: string) => {
    if (!selectedWorkspaceId) return
    setWikiLoading(true)
    try {
      const res = await api.getWikiPage(selectedWorkspaceId, path)
      setWikiContent(res.content)
      setSelectedWikiPage(path)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load wiki page')
    } finally { setWikiLoading(false) }
  }

  const handleCreateSkill = async () => {
    if (!skillName.trim() || !skillIntent.trim() || !selectedWorkspaceId) return
    setSkillLoading(true)
    try {
      const res = await api.createSkill(selectedWorkspaceId, skillName.trim(), skillIntent.trim())
      setSkillResult(res.result)
      fetchSkills()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Skill creation failed')
    } finally { setSkillLoading(false) }
  }

  const fetchSkills = async () => {
    if (!selectedWorkspaceId) return
    try {
      const res = await api.listSkills(selectedWorkspaceId)
      setSkillsList(res.skills)
    } catch (err) {
      console.error('Failed to list skills:', err)
    }
  }

  useEffect(() => {
    if (activeDocTab === 'skills') fetchSkills()
  }, [activeDocTab, selectedWorkspaceId])

  const sidebarContent = (
    <div className="flex flex-col h-full p-3 gap-3">
      <button
        onClick={() => fileInputRef.current?.click()}
        className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl text-sm font-medium text-[#e0e0e0] bg-[#c8956c]/15 hover:bg-[#c8956c]/25 transition-colors duration-150 cursor-pointer border-none"
      >
        <Upload className="w-4 h-4" />
        Upload Document
      </button>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.pptx,.xlsx,.html,.md,.txt,.csv"
        onChange={(e) => handleFileUpload(e.target.files)}
        className="hidden"
      />

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#555]" />
        <input
          type="text" placeholder="Search documents..."
          value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
          className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl pl-9 pr-3 py-2 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:outline-none focus:border-[#c8956c]/50"
        />
      </div>

      <div className="text-[10px] uppercase tracking-wider text-[#555] font-semibold px-1">OpenKB</div>
      <div className="flex-1 overflow-y-auto min-h-0 space-y-1">
        {[
          { id: 'upload', label: 'Upload', icon: Upload },
          { id: 'query', label: 'Query', icon: MessageSquare },
          { id: 'chat', label: 'Chat', icon: MessageSquare },
          { id: 'wiki', label: 'Wiki', icon: BookOpen },
          { id: 'skills', label: 'Skills', icon: Wrench },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveDocTab(tab.id as typeof activeDocTab)}
            className={`w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm text-left transition-colors duration-150 cursor-pointer border-none ${
              activeDocTab === tab.id ? 'bg-white/[0.06] text-[#e0e0e0]' : 'text-[#999] hover:text-[#e0e0e0] hover:bg-white/[0.03]'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {wikiPages.length > 0 && (
        <div className="flex-1 overflow-y-auto min-h-0 space-y-1">
          <div className="text-[10px] uppercase tracking-wider text-[#555] font-semibold px-1">Wiki Pages</div>
          {wikiPages.filter(p => p.title.toLowerCase().includes(searchQuery.toLowerCase())).slice(0, 20).map(page => (
            <button
              key={page.path}
              onClick={() => { setActiveDocTab('wiki'); loadWikiPage(page.path) }}
              className={`w-full text-left px-3 py-1.5 rounded-lg text-xs transition-colors duration-150 cursor-pointer border-none truncate ${
                selectedWikiPage === page.path ? 'text-[#c8956c]' : 'text-[#555] hover:text-[#999]'
              }`}
            >
              <ChevronRight className="w-3 h-3 inline mr-1" />
              {page.title}
            </button>
          ))}
        </div>
      )}

      {stats && (
        <div className="liquid-glass rounded-xl p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-wider text-[#555] font-semibold">OpenKB Stats</span>
            <button
              onClick={handleRecompile}
              disabled={recompiling}
              className="flex items-center gap-1 text-[10px] text-[#c8956c] hover:text-[#e0e0e0] disabled:opacity-50 cursor-pointer bg-transparent border-none transition-colors"
              title="Recompile all documents"
            >
              {recompiling ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
              Recompile
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="text-center p-2 rounded-lg bg-white/[0.03]">
              <div className="text-lg font-semibold text-[#c8956c]">{stats.document_count}</div>
              <div className="text-[10px] text-[#555]">Docs</div>
            </div>
            <div className="text-center p-2 rounded-lg bg-white/[0.03]">
              <div className="text-lg font-semibold text-[#c8956c]">{stats.concept_count}</div>
              <div className="text-[10px] text-[#555]">Concepts</div>
            </div>
            <div className="text-center p-2 rounded-lg bg-white/[0.03]">
              <div className="text-lg font-semibold text-[#c8956c]">{stats.entity_count}</div>
              <div className="text-[10px] text-[#555]">Entities</div>
            </div>
            <div className="text-center p-2 rounded-lg bg-white/[0.03]">
              <div className="text-lg font-semibold text-[#c8956c]">{stats.summary_count}</div>
              <div className="text-[10px] text-[#555]">Summaries</div>
            </div>
          </div>
          <div className="text-[10px] text-[#555] text-center">{(stats.wiki_size_bytes / 1024).toFixed(1)} KB wiki</div>
        </div>
      )}

      <button
        onClick={handleResearchGaps}
        disabled={researchGapsLoading}
        className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl text-sm font-medium text-[#e0e0e0] bg-white/[0.05] hover:bg-white/[0.08] transition-colors duration-150 cursor-pointer border-none disabled:opacity-50"
      >
        {researchGapsLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}
        Research Gaps
      </button>

      <div className="mt-auto pt-3 border-t border-white/[0.06] flex items-center justify-between gap-2">
        <span className="text-xs text-[#555] truncate max-w-[140px]">{user?.email}</span>
        <button onClick={signOut} className="text-xs text-[#c45a5a] hover:text-[#e0e0e0] transition-colors duration-150 cursor-pointer bg-transparent border-none">Sign Out</button>
      </div>
    </div>
  )

  const mainContent = (
    <div className="flex-1 overflow-hidden flex flex-col">
      {/* Upload Tab */}
      {activeDocTab === 'upload' && (
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-2xl mx-auto space-y-6">
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { e.preventDefault(); handleFileUpload(e.dataTransfer.files) }}
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-white/[0.1] rounded-2xl p-12 text-center cursor-pointer hover:border-[#c8956c]/30 hover:bg-white/[0.02] transition-all duration-150"
            >
              <Upload className="w-12 h-12 mx-auto text-[#555] mb-4" />
              <h3 className="text-lg font-semibold text-[#e0e0e0] mb-2">Drop documents here</h3>
              <p className="text-sm text-[#555]">or click to browse. Supports PDF, Word, PowerPoint, Excel, HTML, Markdown, Text, CSV.</p>
              {uploading && (
                <div className="mt-4">
                  <div className="w-full h-2 bg-[#1a1a1a] rounded-full overflow-hidden">
                    <div className="h-full bg-[#c8956c] rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
                  </div>
                  <p className="text-xs text-[#555] mt-1">Uploading... {uploadProgress}%</p>
                </div>
              )}
            </div>

            {documents.length > 0 && (
              <div className="liquid-glass rounded-2xl p-4">
                <h3 className="text-sm font-semibold text-[#e0e0e0] mb-3">Uploaded Documents ({documents.length})</h3>
                <div className="flex flex-col gap-2">
                  {documents.map(doc => (
                    <div key={doc.id} className="flex items-center gap-3 p-2 rounded-xl bg-white/[0.03] hover:bg-white/[0.05] transition-colors group">
                      <File className="w-4 h-4 text-[#555] shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-[#e0e0e0] truncate">{doc.filename}</div>
                        <div className="text-xs text-[#555]">{doc.status} · {(doc.file_size / 1024).toFixed(1)} KB</div>
                      </div>
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                        {selectedWorkspaceId && (
                          <a
                            href={api.downloadDocument(selectedWorkspaceId, doc.id)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 rounded-lg text-[#555] hover:text-[#c8956c] hover:bg-white/[0.05] transition-colors"
                            title="Download"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </a>
                        )}
                        <button
                          onClick={() => handleDeleteDocument(doc.id)}
                          className="p-1.5 rounded-lg text-[#555] hover:text-[#c45a5a] hover:bg-[#c45a5a]/10 transition-colors cursor-pointer border-none"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {wikiPages.length > 0 && (
              <div className="liquid-glass rounded-2xl p-4">
                <h3 className="text-sm font-semibold text-[#e0e0e0] mb-3">Wiki Pages ({wikiPages.length})</h3>
                <div className="flex flex-wrap gap-2">
                  {wikiPages.slice(0, 30).map(page => (
                    <button
                      key={page.path}
                      onClick={() => { setActiveDocTab('wiki'); loadWikiPage(page.path) }}
                      className="px-3 py-1.5 text-xs rounded-lg bg-white/[0.03] text-[#999] hover:text-[#c8956c] hover:bg-[#c8956c]/10 transition-colors cursor-pointer border-none"
                    >
                      {page.title}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Query Tab */}
      {activeDocTab === 'query' && (
        <div className="flex-1 overflow-hidden flex flex-col p-6">
          <div className="max-w-2xl mx-auto w-full space-y-4">
            <div className="liquid-glass rounded-2xl p-4">
              <h3 className="text-sm font-semibold text-[#e0e0e0] mb-3">Ask Your Documents</h3>
              <div className="flex gap-2">
                <input
                  type="text" value={question} onChange={e => setQuestion(e.target.value)}
                  placeholder="What are the key findings from our research papers?"
                  className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-2.5 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:outline-none focus:border-[#c8956c]/50"
                  onKeyDown={e => { if (e.key === 'Enter') handleQuery() }}
                />
                <button
                  onClick={handleQuery}
                  disabled={!question.trim() || queryLoading}
                  className="px-4 py-2.5 rounded-xl text-sm font-medium bg-[#c8956c]/15 text-[#c8956c] hover:bg-[#c8956c]/25 disabled:opacity-50 cursor-pointer border-none transition-colors"
                >
                  {queryLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {queryAnswer && (
              <div className="liquid-glass rounded-2xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h4 className="text-xs uppercase tracking-wider text-[#555] font-semibold">Answer</h4>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={handleSaveQueryToNotes}
                      disabled={querySaving}
                      className="flex items-center gap-1 text-[10px] text-[#c8956c] hover:text-[#e0e0e0] disabled:opacity-50 cursor-pointer bg-transparent border-none transition-colors"
                    >
                      {querySaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <BookCopy className="w-3 h-3" />}
                      Save to Notes
                    </button>
                    <button onClick={() => setQueryAnswer('')} className="text-[#555] hover:text-[#999] cursor-pointer bg-transparent border-none"><X className="w-3 h-3" /></button>
                  </div>
                </div>
                <MarkdownPreview content={queryAnswer} onNavigate={handleWikiNavigate} />
              </div>
            )}

            {queryHistory.length > 0 && (
              <div className="liquid-glass rounded-2xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs uppercase tracking-wider text-[#555] font-semibold">Query History ({queryHistory.length})</h4>
                  <button
                    onClick={() => setShowHistory(!showHistory)}
                    className="text-[10px] text-[#555] hover:text-[#999] cursor-pointer bg-transparent border-none transition-colors"
                  >
                    {showHistory ? 'Collapse' : 'Expand'}
                  </button>
                </div>
                {showHistory && (
                  <div className="flex flex-col gap-2 max-h-60 overflow-y-auto">
                    {queryHistory.map((item, i) => (
                      <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-white/[0.03] group">
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-[#e0e0e0] truncate">{item.question}</div>
                          <div className="text-[10px] text-[#555]">{new Date(item.timestamp).toLocaleString()}</div>
                        </div>
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => { setQuestion(item.question); setQueryAnswer(item.answer); }}
                            className="p-1 rounded text-[#555] hover:text-[#c8956c] cursor-pointer bg-transparent border-none"
                            title="Load"
                          >
                            <RefreshCw className="w-3 h-3" />
                          </button>
                          <button
                            onClick={() => handleDeleteHistoryItem(i)}
                            className="p-1 rounded text-[#555] hover:text-[#c45a5a] cursor-pointer bg-transparent border-none"
                            title="Delete"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Chat Tab */}
      {activeDocTab === 'chat' && (
        <div className="flex-1 overflow-hidden flex flex-col p-6">
          <div className="max-w-2xl mx-auto w-full h-full flex flex-col">
            <div className="flex-1 overflow-y-auto space-y-4 mb-4 min-h-0">
              {chatMessages.length === 0 && (
                <div className="flex items-center justify-center h-full text-[#555] text-sm">
                  Start a conversation about your documents
                </div>
              )}
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
                    msg.role === 'user'
                      ? 'bg-[#c8956c]/20 text-[#e0e0e0] rounded-tr-sm'
                      : 'bg-white/[0.05] text-[#e0e0e0] rounded-tl-sm'
                  }`}>
                    <MarkdownPreview content={msg.content} onNavigate={handleWikiNavigate} />
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="flex justify-start">
                  <div className="bg-white/[0.05] rounded-2xl rounded-tl-sm px-4 py-3">
                    <Loader2 className="w-4 h-4 text-[#c8956c] animate-spin" />
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
            <div className="flex gap-2 shrink-0">
              <input
                type="text" value={chatInput} onChange={e => setChatInput(e.target.value)}
                placeholder="Ask about your documents..."
                className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-2.5 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:outline-none focus:border-[#c8956c]/50"
                onKeyDown={e => { if (e.key === 'Enter') handleChat() }}
              />
              <button
                onClick={handleChat}
                disabled={!chatInput.trim() || chatLoading}
                className="px-4 py-2.5 rounded-xl text-sm font-medium bg-[#c8956c]/15 text-[#c8956c] hover:bg-[#c8956c]/25 disabled:opacity-50 cursor-pointer border-none transition-colors"
              >
                {chatLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Wiki Tab */}
      {activeDocTab === 'wiki' && (
        <div className="flex-1 overflow-hidden flex">
          <div className="w-56 flex-shrink-0 overflow-y-auto border-r border-white/[0.06] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[#555] font-semibold mb-2">Wiki Pages</div>
            {wikiPages.map(page => (
              <button
                key={page.path}
                onClick={() => loadWikiPage(page.path)}
                className={`w-full text-left px-2 py-1.5 rounded-lg text-xs transition-colors cursor-pointer border-none truncate ${
                  selectedWikiPage === page.path ? 'bg-white/[0.06] text-[#c8956c]' : 'text-[#555] hover:text-[#999] hover:bg-white/[0.03]'
                }`}
              >
                {page.title}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-y-auto p-6">
            {wikiLoading ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="w-8 h-8 text-[#c8956c] animate-spin" />
              </div>
            ) : selectedWikiPage ? (
              <div className="max-w-[42rem] mx-auto">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-[#c8956c]" />
                    <span className="text-xs text-[#555]">{selectedWikiPage}</span>
                  </div>
                  {selectedWorkspaceId && (
                    <a
                      href={api.downloadWikiZip(selectedWorkspaceId)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 text-[10px] text-[#c8956c] hover:text-[#e0e0e0] transition-colors"
                      title="Download wiki as ZIP for Obsidian"
                    >
                      <FolderOpen className="w-3.5 h-3.5" />
                      Open in Obsidian
                    </a>
                  )}
                </div>
                <MarkdownPreview content={wikiContent} onNavigate={handleWikiNavigate} />
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-[#555]">
                Select a wiki page from the sidebar
              </div>
            )}
          </div>
        </div>
      )}

      {/* Skills Tab */}
      {activeDocTab === 'skills' && (
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-2xl mx-auto space-y-6">
            <div className="liquid-glass rounded-2xl p-4">
              <h3 className="text-sm font-semibold text-[#e0e0e0] mb-3">Skill Factory</h3>
              <p className="text-xs text-[#555] mb-3">Distill a redistributable agent skill from your compiled wiki.</p>
              <div className="space-y-3">
                <div>
                  <label className="text-xs uppercase tracking-wider text-[#555] font-semibold mb-1 block">Skill Name</label>
                  <input
                    type="text" value={skillName} onChange={e => setSkillName(e.target.value)}
                    placeholder="e.g. research-analyst"
                    className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:outline-none focus:border-[#c8956c]/50"
                  />
                </div>
                <div>
                  <label className="text-xs uppercase tracking-wider text-[#555] font-semibold mb-1 block">Intent</label>
                  <input
                    type="text" value={skillIntent} onChange={e => setSkillIntent(e.target.value)}
                    placeholder="e.g. Analyze financial reports and extract key metrics"
                    className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:outline-none focus:border-[#c8956c]/50"
                  />
                </div>
                <button
                  onClick={handleCreateSkill}
                  disabled={!skillName.trim() || !skillIntent.trim() || skillLoading}
                  className="flex items-center gap-2 py-2.5 px-4 rounded-xl text-sm font-medium bg-[#c8956c]/15 text-[#c8956c] hover:bg-[#c8956c]/25 disabled:opacity-50 cursor-pointer border-none transition-colors"
                >
                  {skillLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  Generate Skill
                </button>
              </div>

              {skillResult && (
                <div className="mt-4 p-3 rounded-xl bg-[#7dac5a]/10 border border-[#7dac5a]/20 text-[#7dac5a] text-xs font-mono whitespace-pre-wrap">
                  {skillResult}
                </div>
              )}

              {/* Skill Controls */}
              {skillsList.length > 0 && (
                <div className="mt-4 pt-4 border-t border-white/[0.06]">
                  <div className="text-[10px] uppercase tracking-wider text-[#555] font-semibold mb-2">
                    Skill Controls {selectedSkill && <span className="text-[#c8956c]">· {selectedSkill}</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSkillAction('validate')}
                      disabled={skillActionLoading !== null || !selectedSkill}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] bg-[#7dac5a]/10 text-[#7dac5a] hover:bg-[#7dac5a]/20 disabled:opacity-50 cursor-pointer border-none transition-colors"
                    >
                      {skillActionLoading === 'validate' ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle className="w-3 h-3" />}
                      Validate
                    </button>
                    <button
                      onClick={() => handleSkillAction('eval')}
                      disabled={skillActionLoading !== null || !selectedSkill}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] bg-[#c8956c]/10 text-[#c8956c] hover:bg-[#c8956c]/20 disabled:opacity-50 cursor-pointer border-none transition-colors"
                    >
                      {skillActionLoading === 'eval' ? <Loader2 className="w-3 h-3 animate-spin" /> : <AlertTriangle className="w-3 h-3" />}
                      Evaluate
                    </button>
                    <button
                      onClick={() => handleSkillAction('rollback')}
                      disabled={skillActionLoading !== null || !selectedSkill}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] bg-[#c45a5a]/10 text-[#c45a5a] hover:bg-[#c45a5a]/20 disabled:opacity-50 cursor-pointer border-none transition-colors"
                    >
                      {skillActionLoading === 'rollback' ? <Loader2 className="w-3 h-3 animate-spin" /> : <RotateCcw className="w-3 h-3" />}
                      Rollback
                    </button>
                  </div>
                  {skillActionResult && (
                    <div className="mt-2 p-2 rounded-lg bg-white/[0.03] text-[10px] text-[#999]">
                      {skillActionResult}
                    </div>
                  )}
                </div>
              )}
            </div>

            {skillsList.length > 0 && (
              <div className="liquid-glass rounded-2xl p-4">
                <h3 className="text-sm font-semibold text-[#e0e0e0] mb-3">Generated Skills</h3>
                <div className="flex flex-col gap-2">
                  {skillsList.map(skill => (
                    <button
                      key={skill}
                      onClick={() => setSelectedSkill(skill)}
                      className={`flex items-center gap-2 p-2 rounded-xl text-left transition-colors cursor-pointer border-none ${
                        selectedSkill === skill ? 'bg-[#c8956c]/10 text-[#c8956c]' : 'bg-white/[0.03] text-[#e0e0e0] hover:bg-white/[0.05]'
                      }`}
                    >
                      <Wrench className="w-4 h-4 text-[#c8956c]" />
                      <span className="text-sm">{skill}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
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
