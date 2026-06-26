import { useEffect, useRef } from 'react'
import { moonConfig } from '../config'

interface CelestialWidgetProps {
  size?: number
}

// Synodic month for moon phase calculation
const SYNODIC_MONTH = 29.53059
const REFERENCE_NEW_MOON = new Date('2024-01-11T00:00:00Z').getTime()

function getMoonPhase(date: Date = new Date()): number {
  const diff = date.getTime() - REFERENCE_NEW_MOON
  const days = diff / (1000 * 60 * 60 * 24)
  const phase = (days % SYNODIC_MONTH) / SYNODIC_MONTH
  return phase < 0 ? phase + 1 : phase
}

function getPhaseLabel(phase: number): string {
  const index = Math.round(phase * 8) % 8
  return moonConfig.phaseLabels[index]
}

function getTimeOfDay(hour: number): 'night' | 'dawn' | 'day' | 'dusk' {
  if (hour >= 5 && hour < 7) return 'dawn'
  if (hour >= 7 && hour < 17) return 'day'
  if (hour >= 17 && hour < 19) return 'dusk'
  return 'night'
}

function getSunPosition(hour: number, minute: number): number {
  // Sun rises at 6:00, peaks at 12:00, sets at 18:00
  const totalMinutes = hour * 60 + minute
  const sunrise = 6 * 60
  const sunset = 18 * 60
  
  if (totalMinutes < sunrise || totalMinutes > sunset) return -1
  
  // Map to 0-1 arc (0 = sunrise, 0.5 = noon, 1 = sunset)
  return (totalMinutes - sunrise) / (sunset - sunrise)
}

export default function CelestialWidget({ size = 48 }: CelestialWidgetProps) {
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

    let animId: number

    const render = () => {
      const now = new Date()
      const hour = now.getHours()
      const minute = now.getMinutes()
      const timeOfDay = getTimeOfDay(hour + minute / 60)
      
      ctx.clearRect(0, 0, size, size)
      
      const cx = size / 2
      const cy = size / 2
      const r = (size / 2) - 2

      // Sky gradient based on time of day
      let skyGradient: CanvasGradient
      
      if (timeOfDay === 'day') {
        // Day: warm blue sky
        skyGradient = ctx.createLinearGradient(0, 0, 0, size)
        skyGradient.addColorStop(0, '#1a2332')
        skyGradient.addColorStop(1, '#0d1a2d')
      } else if (timeOfDay === 'dawn') {
        // Dawn: warm orange/pink
        skyGradient = ctx.createLinearGradient(0, 0, 0, size)
        skyGradient.addColorStop(0, '#2a1a10')
        skyGradient.addColorStop(0.5, '#1a1510')
        skyGradient.addColorStop(1, '#0d1210')
      } else if (timeOfDay === 'dusk') {
        // Dusk: warm purple/orange
        skyGradient = ctx.createLinearGradient(0, 0, 0, size)
        skyGradient.addColorStop(0, '#1a1020')
        skyGradient.addColorStop(0.5, '#151015')
        skyGradient.addColorStop(1, '#0d0d12')
      } else {
        // Night: deep dark
        skyGradient = ctx.createLinearGradient(0, 0, 0, size)
        skyGradient.addColorStop(0, '#0a0a15')
        skyGradient.addColorStop(1, '#050508')
      }

      // Draw sky background
      ctx.fillStyle = skyGradient
      ctx.beginPath()
      ctx.arc(cx, cy, r, 0, Math.PI * 2)
      ctx.fill()

      // Draw stars at night (twinkling)
      if (timeOfDay === 'night' || timeOfDay === 'dawn' || timeOfDay === 'dusk') {
        const seed = now.getDate() + now.getMonth() * 31 // Stable seed for the day
        const starCount = 12
        for (let i = 0; i < starCount; i++) {
          const starSeed = (seed * 997 + i * 331) & 0x7fffffff
          const starR = ((starSeed % 100) / 100) * r * 0.8
          const starAngle = ((starSeed >> 8) % 360) * Math.PI / 180
          const starX = cx + Math.cos(starAngle) * starR
          const starY = cy + Math.sin(starAngle) * starR
          
          // Twinkle based on time
          const twinkle = Math.sin((now.getTime() / 1000 + i * 1.7) * 2) * 0.5 + 0.5
          const starAlpha = timeOfDay === 'night' ? twinkle * 0.8 : twinkle * 0.3
          
          ctx.fillStyle = `rgba(255, 255, 240, ${starAlpha})`
          ctx.beginPath()
          ctx.arc(starX, starY, 0.5 + twinkle * 0.5, 0, Math.PI * 2)
          ctx.fill()
        }
      }

      if (timeOfDay === 'day') {
        // Draw sun
        const sunProgress = getSunPosition(hour, minute)
        const sunAngle = sunProgress * Math.PI // 0 to PI (left to right arc)
        const sunDist = r * 0.6
        const sunX = cx - Math.cos(sunAngle) * sunDist
        const sunY = cy - Math.sin(sunAngle) * sunDist * 0.5 + r * 0.2
        
        // Sun glow
        const glowGradient = ctx.createRadialGradient(sunX, sunY, 0, sunX, sunY, r * 0.8)
        glowGradient.addColorStop(0, 'rgba(255, 200, 100, 0.3)')
        glowGradient.addColorStop(1, 'rgba(255, 200, 100, 0)')
        ctx.fillStyle = glowGradient
        ctx.beginPath()
        ctx.arc(sunX, sunY, r * 0.8, 0, Math.PI * 2)
        ctx.fill()
        
        // Sun disc
        ctx.fillStyle = '#ffd470'
        ctx.beginPath()
        ctx.arc(sunX, sunY, r * 0.18, 0, Math.PI * 2)
        ctx.fill()
        
        // Sun rays
        ctx.strokeStyle = 'rgba(255, 200, 100, 0.2)'
        ctx.lineWidth = 0.5
        for (let i = 0; i < 8; i++) {
          const rayAngle = (i / 8) * Math.PI * 2 + (now.getTime() / 5000)
          const rayInner = r * 0.22
          const rayOuter = r * 0.35
          ctx.beginPath()
          ctx.moveTo(sunX + Math.cos(rayAngle) * rayInner, sunY + Math.sin(rayAngle) * rayInner)
          ctx.lineTo(sunX + Math.cos(rayAngle) * rayOuter, sunY + Math.sin(rayAngle) * rayOuter)
          ctx.stroke()
        }
      } else {
        // Draw moon with phase
        const phase = getMoonPhase(now)
        
        // Moon glow
        const moonGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 0.9)
        moonGlow.addColorStop(0, 'rgba(200, 200, 220, 0.15)')
        moonGlow.addColorStop(1, 'rgba(200, 200, 220, 0)')
        ctx.fillStyle = moonGlow
        ctx.beginPath()
        ctx.arc(cx, cy, r * 0.9, 0, Math.PI * 2)
        ctx.fill()
        
        // Dark moon background
        ctx.beginPath()
        ctx.arc(cx, cy, r * 0.22, 0, Math.PI * 2)
        ctx.fillStyle = '#1a1a2e'
        ctx.fill()
        ctx.strokeStyle = 'rgba(200, 200, 220, 0.3)'
        ctx.lineWidth = 0.5
        ctx.stroke()
        
        // Lit portion
        ctx.save()
        ctx.beginPath()
        ctx.arc(cx, cy, r * 0.22, 0, Math.PI * 2)
        ctx.clip()
        
        if (phase <= 0.5) {
          // Waxing: light on right
          ctx.fillStyle = '#d4d4e0'
          ctx.beginPath()
          ctx.arc(cx, cy, r * 0.22, -Math.PI / 2, Math.PI / 2)
          ctx.fill()
          
          const ellipseWidth = r * 0.22 * Math.cos(phase * Math.PI * 2)
          ctx.fillStyle = phase < 0.25 ? '#1a1a2e' : '#d4d4e0'
          ctx.beginPath()
          ctx.ellipse(cx, cy, Math.abs(ellipseWidth), r * 0.22, 0, 0, Math.PI * 2)
          ctx.fill()
        } else {
          // Waning: light on left
          ctx.fillStyle = '#d4d4e0'
          ctx.beginPath()
          ctx.arc(cx, cy, r * 0.22, Math.PI / 2, -Math.PI / 2)
          ctx.fill()
          
          const ellipseWidth = r * 0.22 * Math.cos((phase - 0.5) * Math.PI * 2)
          ctx.fillStyle = phase > 0.75 ? '#1a1a2e' : '#d4d4e0'
          ctx.beginPath()
          ctx.ellipse(cx, cy, Math.abs(ellipseWidth), r * 0.22, 0, 0, Math.PI * 2)
          ctx.fill()
        }
        ctx.restore()
        
        // Craters (subtle)
        ctx.fillStyle = 'rgba(0, 0, 0, 0.1)'
        ctx.beginPath()
        ctx.arc(cx + r * 0.05, cy - r * 0.03, r * 0.04, 0, Math.PI * 2)
        ctx.fill()
        ctx.beginPath()
        ctx.arc(cx - r * 0.06, cy + r * 0.05, r * 0.03, 0, Math.PI * 2)
        ctx.fill()
      }

      // Border ring
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.arc(cx, cy, r, 0, Math.PI * 2)
      ctx.stroke()

      animId = requestAnimationFrame(render)
    }

    animId = requestAnimationFrame(render)

    return () => {
      cancelAnimationFrame(animId)
    }
  }, [size])

  const now = new Date()
  const hour = now.getHours()
  const minute = now.getMinutes()
  const timeOfDay = getTimeOfDay(hour + minute / 60)
  const phase = getMoonPhase(now)
  const phaseLabel = timeOfDay === 'day' ? 'Daytime' : getPhaseLabel(phase)
  
  const timeString = now.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: false 
  })
  const dateString = now.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric' 
  })

  return (
    <div className="flex flex-col items-center gap-1">
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        style={{ width: size, height: size }}
        className="rounded-full"
        title={`${timeString} — ${phaseLabel}`}
      />
      <div className="text-[10px] text-[#555] leading-tight text-center">
        <div>{dateString}</div>
        <div className="text-[#666]">{phaseLabel}</div>
      </div>
    </div>
  )
}
