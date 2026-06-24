import { useEffect, useRef } from 'react'

export default function RainOnGlass() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvasEl = canvasRef.current
    if (!canvasEl) return

    const ctx = canvasEl.getContext('2d')
    if (!ctx) return

    const W = canvasEl.width

    const resize = () => {
      canvasEl.width = window.innerWidth
      canvasEl.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    // Raindrop state
    interface Drop {
      x: number
      y: number
      r: number
      speed: number
      trail: { x: number; y: number; r: number }[]
      merged: boolean
    }

    const drops: Drop[] = []
    const MAX_DROPS = 900
    const TRAIL_LENGTH = 8

    function createDrop(): Drop {
      return {
        x: Math.random() * W,
        y: -20,
        r: 1 + Math.random() * 3,
        speed: 2 + Math.random() * 8,
        trail: [],
        merged: false,
      }
    }

    // Initialize drops
    for (let i = 0; i < MAX_DROPS; i++) {
      const d = createDrop()
      d.y = Math.random() * canvasEl.height
      drops.push(d)
    }

    let animId: number

    const render = () => {
      ctx.clearRect(0, 0, canvasEl.width, canvasEl.height)

      // Procedural cityscape background (dark silhouette)
      const bgCtx = ctx
      bgCtx.fillStyle = '#0a0a0a'
      bgCtx.fillRect(0, 0, canvasEl.width, canvasEl.height)

      // Draw cityscape silhouettes
      bgCtx.fillStyle = '#111'
      const blockWidth = 30 + Math.random() * 50
      for (let x = 0; x < canvasEl.width; x += blockWidth) {
        const height = 50 + Math.random() * 150
        bgCtx.fillRect(x, canvasEl.height - height, blockWidth - 2, height)
      }

      // Draw raindrops
      drops.forEach((d) => {
        if (d.merged) return

        // Update trail
        d.trail.unshift({ x: d.x, y: d.y, r: d.r })
        if (d.trail.length > TRAIL_LENGTH) d.trail.pop()

        // Move
        d.y += d.speed
        d.x += Math.sin(d.y * 0.01) * 0.5

        // Draw trail
        d.trail.forEach((t, i) => {
          const alpha = (1 - i / TRAIL_LENGTH) * 0.3
          bgCtx.beginPath()
          bgCtx.arc(t.x, t.y, t.r * (1 - i / TRAIL_LENGTH * 0.5), 0, Math.PI * 2)
          bgCtx.fillStyle = `rgba(150, 160, 180, ${alpha})`
          bgCtx.fill()
        })

        // Draw drop
        bgCtx.beginPath()
        bgCtx.arc(d.x, d.y, d.r, 0, Math.PI * 2)
        bgCtx.fillStyle = 'rgba(180, 190, 210, 0.6)'
        bgCtx.fill()

        // Refraction highlight
        bgCtx.beginPath()
        bgCtx.arc(d.x - d.r * 0.3, d.y - d.r * 0.3, d.r * 0.4, 0, Math.PI * 2)
        bgCtx.fillStyle = 'rgba(255, 255, 255, 0.3)'
        bgCtx.fill()

        // Reset if off screen
        if (d.y > canvasEl.height + 20) {
          d.y = -20
          d.x = Math.random() * canvasEl.width
          d.trail = []
          d.merged = false
        }
      })

      // CSS filter approximation: saturate(0.7) brightness(0.55)
      // We apply this by drawing a semi-transparent overlay
      bgCtx.fillStyle = 'rgba(0, 0, 0, 0.45)'
      bgCtx.fillRect(0, 0, canvasEl.width, canvasEl.height)

      animId = requestAnimationFrame(render)
    }

    animId = requestAnimationFrame(render)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full"
      style={{ display: 'block' }}
    />
  )
}
