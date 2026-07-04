import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router'
import {
  Key, Cpu, Search, Palette, BookOpen, Database,
  ChevronRight, Check, Eye, EyeOff, ArrowLeft, Save, RefreshCw,
  Layers
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { api } from '../../api/client'
import { useResearch } from '../../lib/researchContext'
import type { SettingsResponse, AppSettingsPatch } from '../../types/api'
import Layout from '../../components/layout/Layout'

// ─── Types are now imported from types/api.ts
// Re-exported here for local readability
type LocalSettingsResponse = SettingsResponse

// ─── Section definitions ──────────────────────────────────────────────────────

const SECTIONS = [
  { id: 'llm',        label: 'LLM Defaults',       icon: Cpu        },
  { id: 'keys',       label: 'API Keys',            icon: Key        },
  { id: 'research',   label: 'Research Defaults',   icon: BookOpen   },
  { id: 'search',     label: 'Search',              icon: Search     },
  { id: 'appearance', label: 'Appearance',          icon: Palette    },
  { id: 'workspace',  label: 'Workspace',           icon: Layers     },
  { id: 'data',       label: 'Data & Privacy',      icon: Database   },
] as const

type SectionId = typeof SECTIONS[number]['id']

// ─── Sub-components ───────────────────────────────────────────────────────────

function SectionLabel({ text }: { text: string }) {
  return (
    <p className="sidebar-section-label">{text}</p>
  )
}

function SettingRow({
  label,
  description,
  children,
}: {
  label: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-4 border-b border-white/[0.04] last:border-b-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[#ccc] font-medium leading-5">{label}</p>
        {description && <p className="text-xs text-[#555] mt-0.5 leading-4">{description}</p>}
      </div>
      <div className="shrink-0 w-60">{children}</div>
    </div>
  )
}

function ApiKeyField({
  label,
  isSet,
  placeholder,
  value,
  onChange,
}: {
  label: string
  isSet: boolean
  placeholder: string
  value: string
  onChange: (v: string) => void
}) {
  const [show, setShow] = useState(false)

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label className="text-xs text-[#666]">{label}</label>
        {isSet && (
          <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-medium">
            <Check className="w-2.5 h-2.5" /> Active
          </span>
        )}
      </div>
      <div className="relative">
        <input
          type={show ? 'text' : 'password'}
          placeholder={isSet ? '•'.repeat(24) : placeholder}
          value={value}
          onChange={e => onChange(e.target.value)}
          className="settings-input pr-10"
          autoComplete="off"
          spellCheck={false}
        />
        <button
          type="button"
          onClick={() => setShow(s => !s)}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#444] hover:text-[#888] transition-colors cursor-pointer bg-transparent border-none"
        >
          {show ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
        </button>
      </div>
    </div>
  )
}

function SelectField({
  value,
  options,
  onChange,
}: {
  value: string
  options: { value: string; label: string }[]
  onChange: (v: string) => void
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="settings-input"
    >
      {options.map(o => (
        <option key={o.value} value={o.value} className="bg-[#111]">
          {o.label}
        </option>
      ))}
    </select>
  )
}

function SliderField({
  value,
  min,
  max,
  onChange,
  labels,
}: {
  value: number
  min: number
  max: number
  onChange: (v: number) => void
  labels?: string[]
}) {
  return (
    <div className="space-y-2">
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full accent-[#c8956c]"
      />
      {labels && (
        <div className="flex justify-between text-[10px] text-[#444]">
          {labels.map((l, i) => (
            <span key={i} className={value === i + min ? 'text-[#c8956c]' : ''}>{l}</span>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function SettingsModule() {
  const navigate = useNavigate()
  const { selectedWorkspaceId: workspaceId } = useResearch()
  const [activeSection, setActiveSection] = useState<SectionId>('llm')
  const [saving, setSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saved' | 'error'>('idle')
  const [loading, setLoading] = useState(true)

  // Form state
  const [remote, setRemote] = useState<LocalSettingsResponse | null>(null)
  const [localKeys, setLocalKeys] = useState({ openrouter: '', groq: '' })
  const [form, setForm] = useState({
    default_provider: 'openrouter',
    default_model: 'openrouter/qwen/qwen3-235b-a22b:free',
    default_depth: 3,
    default_format: 'academic',
    default_length: 'full',
    default_audience: 'researcher',
    background_mode: 'moonlit',
    accent_color: '#c8956c',
    sidebar_expanded: true,
  })

  // Load settings
  const loadSettings = useCallback(async () => {
    if (!workspaceId) {
      setLoading(false)
      setRemote(null)
      return
    }
    setLoading(true)
    try {
      const data = await api.getSettings(workspaceId)
      setRemote(data)
      setForm(prev => ({
        ...prev,
        default_provider: data.default_provider,
        default_model: data.default_model,
        default_depth: data.default_depth,
        default_format: data.default_format,
        default_length: data.default_length,
        default_audience: data.default_audience,
        background_mode: data.background_mode,
        accent_color: data.accent_color,
        sidebar_expanded: data.sidebar_expanded,
      }))
    } catch (e) {
      console.warn('Settings load failed, using defaults', e)
    } finally {
      setLoading(false)
    }
  }, [workspaceId])

  useEffect(() => {
    loadSettings()
  }, [workspaceId, loadSettings])

  // Save handler
  const handleSave = async () => {
    if (!workspaceId) {
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2500)
      return
    }
    setSaving(true)
    setSaveStatus('idle')
    try {
      const payload: AppSettingsPatch = { ...form }
      if (localKeys.openrouter) payload.openrouter_api_key = localKeys.openrouter
      if (localKeys.groq) payload.groq_api_key = localKeys.groq

      await api.updateSettings(workspaceId, payload)
      setSaveStatus('saved')
      setLocalKeys({ openrouter: '', groq: '' })
      loadSettings()
      setTimeout(() => setSaveStatus('idle'), 2500)
    } catch {
      setSaveStatus('error')
    } finally {
      setSaving(false)
    }
  }

  const update = <K extends keyof typeof form>(key: K, value: typeof form[K]) =>
    setForm(prev => ({ ...prev, [key]: value }))

  // ─── Section renderers ──────────────────────────────────────────────────

  function renderLLM() {
    return (
      <div className="settings-card space-y-0">
        <SettingRow label="Default Provider" description="Which LLM provider to use by default">
          <SelectField
            value={form.default_provider}
            onChange={v => update('default_provider', v)}
            options={[
              { value: 'openrouter', label: 'OpenRouter' },
              { value: 'groq',       label: 'Groq'       },
            ]}
          />
        </SettingRow>
        <SettingRow label="Default Model" description="Model ID used when none is specified in the research form">
          <input
            value={form.default_model}
            onChange={e => update('default_model', e.target.value)}
            className="settings-input"
            placeholder="e.g. openrouter/qwen/qwen3-235b-a22b:free"
          />
        </SettingRow>
        <SettingRow label="Default Research Depth" description="How many iterations of search + synthesis to run (1 = fastest, 5 = exhaustive)">
          <SliderField
            value={form.default_depth}
            min={1}
            max={5}
            onChange={v => update('default_depth', v)}
            labels={['1', '2', '3', '4', '5']}
          />
        </SettingRow>
      </div>
    )
  }

  function renderKeys() {
    return (
      <div className="space-y-4">
        <div className="settings-card space-y-4">
          <SectionLabel text="OpenRouter" />
          <ApiKeyField
            label="API Key"
            isSet={remote?.openrouter_api_key_set ?? false}
            placeholder="sk-or-…"
            value={localKeys.openrouter}
            onChange={v => setLocalKeys(prev => ({ ...prev, openrouter: v }))}
          />
        </div>
        <div className="settings-card space-y-4">
          <SectionLabel text="Groq" />
          <ApiKeyField
            label="API Key"
            isSet={remote?.groq_api_key_set ?? false}
            placeholder="gsk_…"
            value={localKeys.groq}
            onChange={v => setLocalKeys(prev => ({ ...prev, groq: v }))}
          />
        </div>
        <p className="text-xs text-[#444] px-1">
          Keys are XOR-encoded before storage. Never shared outside your workspace.
        </p>
      </div>
    )
  }

  function renderResearch() {
    return (
      <div className="settings-card space-y-0">
        <SettingRow label="Output Format" description="Report style applied when none is selected">
          <SelectField
            value={form.default_format}
            onChange={v => update('default_format', v)}
            options={[
              { value: 'academic',   label: 'Academic'   },
              { value: 'business',   label: 'Business'   },
              { value: 'technical',  label: 'Technical'  },
              { value: 'product',    label: 'Product'    },
              { value: 'literature', label: 'Literature' },
              { value: 'data',       label: 'Data'       },
            ]}
          />
        </SettingRow>
        <SettingRow label="Report Length" description="Default verbosity of generated reports">
          <SelectField
            value={form.default_length}
            onChange={v => update('default_length', v)}
            options={[
              { value: 'abstract', label: 'Abstract (brief)'    },
              { value: 'short',    label: 'Short summary'       },
              { value: 'full',     label: 'Full report'         },
              { value: 'thesis',   label: 'Thesis (exhaustive)' },
            ]}
          />
        </SettingRow>
        <SettingRow label="Target Audience" description="Writing style and terminology calibration">
          <SelectField
            value={form.default_audience}
            onChange={v => update('default_audience', v)}
            options={[
              { value: 'researcher',  label: 'Researcher'  },
              { value: 'developer',   label: 'Developer'   },
              { value: 'executive',   label: 'Executive'   },
              { value: 'general',     label: 'General'     },
            ]}
          />
        </SettingRow>
      </div>
    )
  }

  function renderSearch() {
    return (
      <div className="settings-card">
        <p className="text-sm text-[#555] py-4">
          Search provider configuration is managed via <code className="text-[#c8956c] text-xs">config.toml</code>.
          DuckDuckGo is the default free provider. GitHub search is auto-enabled when a GitHub token is configured.
        </p>
      </div>
    )
  }

  function renderAppearance() {
    return (
      <div className="settings-card space-y-0">
        <SettingRow label="Background Mode" description="Visual background style">
          <SelectField
            value={form.background_mode}
            onChange={v => update('background_mode', v)}
            options={[
              { value: 'moonlit', label: 'Moonlit Ripple' },
              { value: 'silk',    label: 'Silk Flow'      },
              { value: 'rain',    label: 'Rain on Glass'  },
              { value: 'solid',   label: 'Solid'          },
            ]}
          />
        </SettingRow>
        <SettingRow label="Accent Color" description="Primary accent color (Hex)">
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={form.accent_color}
              onChange={e => update('accent_color', e.target.value)}
              className="w-8 h-8 rounded-lg border border-white/10 cursor-pointer bg-transparent"
            />
            <input
              value={form.accent_color}
              onChange={e => update('accent_color', e.target.value)}
              className="settings-input flex-1"
              placeholder="#c8956c"
            />
          </div>
        </SettingRow>
        <SettingRow label="Sidebar Expanded" description="Keep sidebar panel open by default">
          <button
            onClick={() => update('sidebar_expanded', !form.sidebar_expanded)}
            className={cn(
              'relative w-10 h-5.5 rounded-full transition-colors cursor-pointer border-none',
              form.sidebar_expanded ? 'bg-[#c8956c]' : 'bg-white/10'
            )}
            role="switch"
            aria-checked={form.sidebar_expanded}
          >
            <span
              className={cn(
                'absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform',
                form.sidebar_expanded && 'translate-x-5'
              )}
            />
          </button>
        </SettingRow>
      </div>
    )
  }

  function renderWorkspace() {
    return (
      <div className="settings-card">
        <SettingRow label="Workspace ID" description="Current active workspace">
          <input
            value={workspaceId ?? ''}
            className="settings-input opacity-60"
            readOnly
          />
        </SettingRow>
      </div>
    )
  }

  function renderData() {
    return (
      <div className="settings-card">
        <p className="text-sm text-[#555] py-4">
          Research data, notes, and documents are tied to your workspace and stored in Supabase.
          To export all data, use the Export features within each module. To delete your workspace,
          contact support.
        </p>
      </div>
    )
  }

  const RENDERERS: Record<SectionId, () => React.ReactNode> = {
    llm:        renderLLM,
    keys:       renderKeys,
    research:   renderResearch,
    search:     renderSearch,
    appearance: renderAppearance,
    workspace:  renderWorkspace,
    data:       renderData,
  }

  const activeTitle = SECTIONS.find(s => s.id === activeSection)?.label ?? 'Settings'

  // ─── Render ─────────────────────────────────────────────────────────────

  return (
    <Layout moduleId="settings">
      <div className="flex h-full overflow-hidden bg-transparent">
        {/* Left nav */}
        <aside className="w-52 flex-shrink-0 border-r border-white/[0.06] flex flex-col py-4 gap-0.5 overflow-y-auto bg-black/40 backdrop-blur-md">
          <div className="px-4 pb-3">
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-1.5 text-xs text-[#555] hover:text-[#999] transition-colors cursor-pointer bg-transparent border-none"
            >
              <ArrowLeft className="w-3 h-3" /> Back
            </button>
            <p className="text-sm font-semibold text-[#e0e0e0] mt-2">Settings</p>
            <p className="text-xs text-[#444] mt-0.5">Workspace configuration</p>
          </div>

          <SectionLabel text="Configuration" />

          {SECTIONS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveSection(id)}
              className={cn(
                'w-full text-left flex items-center gap-2.5 px-4 py-2 text-xs transition-colors cursor-pointer bg-transparent border-none',
                activeSection === id
                  ? 'text-[#c8956c] bg-[#c8956c]/[0.08]'
                  : 'text-[#666] hover:text-[#999] hover:bg-white/[0.03]'
              )}
            >
              <Icon className="w-3.5 h-3.5 shrink-0" strokeWidth={activeSection === id ? 2 : 1.5} />
              {label}
              {activeSection === id && <ChevronRight className="w-3 h-3 ml-auto text-[#c8956c]/60" />}
            </button>
          ))}
        </aside>

        {/* Content */}
        <div className="flex-1 overflow-y-auto bg-transparent">
          <div className="max-w-2xl mx-auto px-6 py-8">
            {/* Section header */}
            <div className="mb-6">
              <h1 className="text-xl font-semibold text-[#e0e0e0]">{activeTitle}</h1>
              {remote?.updated_at && (
                <p className="text-xs text-[#444] mt-1">
                  Last saved {new Date(remote.updated_at).toLocaleString()}
                </p>
              )}
            </div>

            {/* Offline Alert Banner */}
            {!workspaceId && (
              <div className="mb-6 px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 flex items-center gap-2 font-mono">
                <span className="shrink-0 font-bold">⚠️ OFFLINE MODE:</span>
                <span>No active workspace selected. Settings are loaded from local defaults.</span>
              </div>
            )}

            {/* Loading state */}
            {loading ? (
              <div className="space-y-4">
                {[1,2,3].map(i => (
                  <div key={i} className="settings-card h-24 animate-pulse" />
                ))}
              </div>
            ) : RENDERERS[activeSection]?.()}

            {/* Save bar */}
            <div className="mt-8 flex items-center gap-3">
              <button
                onClick={handleSave}
                disabled={saving}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all cursor-pointer border-none',
                  saving ? 'opacity-50 cursor-not-allowed' : '',
                  saveStatus === 'saved'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : saveStatus === 'error'
                    ? 'bg-red-500/20 text-red-400'
                    : 'bg-[#c8956c]/20 text-[#c8956c] hover:bg-[#c8956c]/30'
                )}
              >
                {saving ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : saveStatus === 'saved' ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                {saving ? 'Saving…' : saveStatus === 'saved' ? 'Saved' : saveStatus === 'error' ? 'Save failed' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}
