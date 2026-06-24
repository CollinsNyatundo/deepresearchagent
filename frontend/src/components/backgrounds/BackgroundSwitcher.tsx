import { useState } from 'react'
import { useBackground } from '../../hooks/useBackground'
const BACKGROUND_OPTIONS: { value: 'moonlit' | 'silk' | 'rain' | 'solid'; label: string; icon: string }[] = [
  { value: 'moonlit', label: 'Moonlit Ripple', icon: '🌙' },
  { value: 'silk', label: 'Silk Flow', icon: '🧵' },
  { value: 'rain', label: 'Rain on Glass', icon: '🌧️' },
  { value: 'solid', label: 'Solid Color', icon: '⬛' },
]

const SOLID_COLORS: { value: '#000000' | '#1a1a2e' | '#1a1308' | '#0d1f0d'; label: string }[] = [
  { value: '#000000', label: 'Ink Black' },
  { value: '#1a1a2e', label: 'Deep Blue' },
  { value: '#1a1308', label: 'Brown' },
  { value: '#0d1f0d', label: 'Dark Green' },
]

export default function BackgroundSwitcher() {
  const { state, setMode, setSolidColor } = useBackground()
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs text-[#555] hover:text-[#999] transition-colors duration-150 cursor-pointer bg-transparent border-none"
        title="Change background"
      >
        <span className="text-sm">
          {BACKGROUND_OPTIONS.find((b) => b.value === state.mode)?.icon ?? '⬛'}
        </span>
        <span className="hidden sm:inline">Background</span>
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 top-full mt-1 w-48 liquid-glass-strong rounded-xl py-2 z-50 shadow-2xl">
            <div className="px-3 py-1.5 text-xs text-[#555] uppercase tracking-wider font-medium">
              Background
            </div>
            {BACKGROUND_OPTIONS.map((bg) => (
              <button
                key={bg.value}
                onClick={() => {
                  setMode(bg.value)
                  if (bg.value !== 'solid') setOpen(false)
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors duration-150 cursor-pointer border-none bg-transparent ${
                  state.mode === bg.value
                    ? 'text-[#c8956c]'
                    : 'text-[#999] hover:text-[#e0e0e0]'
                }`}
              >
                <span>{bg.icon}</span>
                <span>{bg.label}</span>
              </button>
            ))}

            {state.mode === 'solid' && (
              <div className="mt-2 pt-2 border-t border-white/[0.06]">
                <div className="px-3 py-1.5 text-xs text-[#555] uppercase tracking-wider font-medium">
                  Color
                </div>
                {SOLID_COLORS.map((c) => (
                  <button
                    key={c.value}
                    onClick={() => {
                      setSolidColor(c.value)
                      setOpen(false)
                    }}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors duration-150 cursor-pointer border-none bg-transparent ${
                      state.solidColor === c.value
                        ? 'text-[#c8956c]'
                        : 'text-[#999] hover:text-[#e0e0e0]'
                    }`}
                  >
                    <span
                      className="w-3 h-3 rounded-full inline-block"
                      style={{ backgroundColor: c.value, border: '1px solid rgba(255,255,255,0.1)' }}
                    />
                    <span>{c.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
