import { useEffect, useRef } from 'react'

function getMoonPhase(date: Date = new Date()) {
  let year = date.getFullYear()
  let month = date.getMonth() + 1
  const day = date.getDate()
  
  let c, e, jd, b
  if (month < 3) { year--; month += 12 }
  c = 365.25 * year
  e = 30.6 * month
  jd = c + e + day - 694039.09
  jd /= 29.5305882
  b = Math.floor(jd)
  jd -= b
  b = Math.round(jd * 8)
  if (b >= 8) b = 0
  return b / 8
}

export default function MoonPhaseWidget({ size = 48 }: { size?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = size * dpr
    canvas.height = size * dpr
    ctx.scale(dpr, dpr)

    const phase = getMoonPhase()
    const cx = size / 2
    const cy = size / 2
    const r = (size / 2) - 2

    ctx.clearRect(0, 0, size, size)

    // Draw dark moon background
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.fillStyle = '#1a1a1a'
    ctx.fill()
    ctx.strokeStyle = '#c8956c'
    ctx.lineWidth = 0.5
    ctx.stroke()

    // Draw lit portion based on phase
    ctx.save()
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.clip()

    if (phase <= 0.5) {
      // Waxing: light on right
      ctx.fillStyle = '#c8956c'
      ctx.beginPath()
      ctx.arc(cx, cy, r, -Math.PI / 2, Math.PI / 2)
      ctx.fill()
      
      const ellipseWidth = r * Math.cos(phase * Math.PI * 2)
      ctx.fillStyle = phase < 0.25 ? '#1a1a1a' : '#c8956c'
      ctx.beginPath()
      ctx.ellipse(cx, cy, Math.abs(ellipseWidth), r, 0, 0, Math.PI * 2)
      ctx.fill()
    } else {
      // Waning: light on left
      ctx.fillStyle = '#c8956c'
      ctx.beginPath()
      ctx.arc(cx, cy, r, Math.PI / 2, -Math.PI / 2)
      ctx.fill()
      
      const ellipseWidth = r * Math.cos((phase - 0.5) * Math.PI * 2)
      ctx.fillStyle = phase > 0.75 ? '#1a1a1a' : '#c8956c'
      ctx.beginPath()
      ctx.ellipse(cx, cy, Math.abs(ellipseWidth), r, 0, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.restore()
  }, [size])

  return (
    <canvas
      ref={canvasRef}
      width={size}
      height={size}
      style={{ width: size, height: size }}
      className="rounded-full"
      title="Moon Phase"
    />
  )
}
