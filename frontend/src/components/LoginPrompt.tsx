import { Suspense, lazy } from 'react'
import { AuthModal } from './Auth/AuthModal'

const MoonlitRipple = lazy(() => import('./backgrounds/MoonlitRipple'))

export default function LoginPrompt() {
  return (
    <div className="h-screen w-full relative overflow-hidden">
      {/* Cinematic background - unchanged per user request */}
      <div className="absolute inset-0 z-0">
        <Suspense fallback={<div className="w-full h-full bg-[#050505]" />}>
          <MoonlitRipple />
        </Suspense>
      </div>

      {/* Centered glass panel */}
      <div className="absolute inset-0 z-10 flex items-center justify-center px-4">
        <div 
          className="liquid-glass-strong rounded-[2rem] p-8 w-full max-w-sm"
          style={{ background: 'rgba(255, 255, 255, 0.02)' }}
        >
          <AuthModal opened={true} />
        </div>
      </div>
    </div>
  )
}
