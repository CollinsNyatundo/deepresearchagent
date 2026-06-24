import { useState } from 'react'
import { HexColorPicker } from 'react-colorful'

interface ColorPickerProps {
  color: string
  onChange: (color: string) => void
  label?: string
}

export function ColorPicker({ color, onChange, label }: ColorPickerProps) {
  const [showPicker, setShowPicker] = useState(false)

  return (
    <div className="relative">
      {label && <label className="block text-sm text-[#c4c6d8] mb-2">{label}</label>}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowPicker(!showPicker)}
          className="w-10 h-10 rounded-lg border border-[rgba(255,255,255,0.1)] shadow-sm focus:outline-none focus:ring-2 focus:ring-[#3a7bd5]"
          style={{ backgroundColor: color }}
          aria-label="Pick color"
        />
        <span className="text-sm text-[#c4c6d8] font-mono">{color}</span>
      </div>
      {showPicker && (
        <div className="absolute z-50 mt-2">
          <div className="fixed inset-0" onClick={() => setShowPicker(false)} />
          <HexColorPicker color={color} onChange={onChange} />
        </div>
      )}
    </div>
  )
}
