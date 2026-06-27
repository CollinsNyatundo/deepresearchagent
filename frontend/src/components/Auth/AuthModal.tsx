import React, { useState } from 'react'
import { supabase } from '../../lib/supabase'
import { Eye, EyeOff, Lock, Mail, AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'

type AuthModalProps = {
  opened?: boolean
  onClose?: () => void
}

const isPlaceholderConfig = () => {
  const url = import.meta.env.VITE_SUPABASE_URL || ''
  const key = import.meta.env.VITE_SUPABASE_ANON_KEY || ''
  return url.includes('placeholder') || key.includes('placeholder') || !url || !key
}

export const AuthModal: React.FC<AuthModalProps> = ({ opened = true, onClose }) => {
  const [activeTab, setActiveTab] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (isPlaceholderConfig()) {
      setError('Supabase not configured. Please check your environment variables.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) throw error
      toast.success('Welcome back!')
      onClose?.()
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    if (isPlaceholderConfig()) {
      setError('Supabase not configured. Please check your environment variables.')
      return
    }
    setLoading(true)
    setError(null)
    setInfo(null)
    try {
      const { data, error } = await supabase.auth.signUp({ email, password })
      if (error) throw error
      if (data.session) {
        toast.success('Welcome!')
        onClose?.()
      } else {
        setInfo('Signup successful! Please check your email to confirm your account.')
      }
    } catch (err: any) {
      setError(err.message || 'Signup failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSocialLogin = async (provider: 'google' | 'facebook') => {
    if (isPlaceholderConfig()) {
      setError('Supabase not configured. Cannot perform social login.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: window.location.origin,
        }
      })
      if (error) throw error
    } catch (err: any) {
      setError(err.message || 'Social login failed')
      setLoading(false)
    }
  }

  if (!opened) return null

  const placeholderWarning = isPlaceholderConfig()

  return (
    <div className="auth-glass-container relative flex flex-col justify-center">
      <svg width="0" height="0" className="absolute pointer-events-none">
        <defs>
          <clipPath id="auth-blob-clip" clipPathUnits="objectBoundingBox">
            <path d="M 0.179 0.070 C 0.385 0.100, 0.615 0.040, 0.821 0.070 C 0.910 0.080, 0.962 0.110, 0.962 0.200 C 0.962 0.320, 0.885 0.440, 0.885 0.540 C 0.885 0.640, 0.962 0.720, 0.962 0.800 C 0.962 0.880, 0.897 0.940, 0.795 0.950 C 0.590 0.920, 0.385 0.970, 0.205 0.940 C 0.115 0.930, 0.051 0.880, 0.051 0.790 C 0.051 0.700, 0.115 0.600, 0.115 0.500 C 0.115 0.400, 0.038 0.300, 0.051 0.200 C 0.051 0.120, 0.115 0.080, 0.179 0.070 Z" />
          </clipPath>
        </defs>
      </svg>

      <div 
        className="absolute inset-0 auth-glass-backdrop z-0 pointer-events-none"
        style={{ clipPath: 'url(#auth-blob-clip)' }}
      />

      <div className="absolute inset-0 pointer-events-none z-20">
        <svg className="w-full h-full" viewBox="0 0 390 500" preserveAspectRatio="none" fill="none">
          <defs>
            <radialGradient id="glass-radial" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
              <stop offset="0%" stopColor="rgba(15, 12, 10, 0.2)" />
              <stop offset="70%" stopColor="rgba(10, 7, 5, 0.5)" />
              <stop offset="100%" stopColor="rgba(4, 2, 1, 0.8)" />
            </radialGradient>
            <linearGradient id="gold-base" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#ffd899" stopOpacity="0.4" />
              <stop offset="35%" stopColor="#c8956c" stopOpacity="0.1" />
              <stop offset="70%" stopColor="#9a6f43" stopOpacity="0.1" />
              <stop offset="100%" stopColor="#c8956c" stopOpacity="0.4" />
            </linearGradient>
            <linearGradient id="top-right-glow" x1="30%" y1="0%" x2="100%" y2="50%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0" />
              <stop offset="50%" stopColor="#ffd899" stopOpacity="0.8" />
              <stop offset="75%" stopColor="#ffffff" stopOpacity="0.95" />
              <stop offset="100%" stopColor="#ffd899" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="bottom-right-glow" x1="100%" y1="50%" x2="50%" y2="100%">
              <stop offset="0%" stopColor="#ffd899" stopOpacity="0" />
              <stop offset="50%" stopColor="#e8b97c" stopOpacity="0.8" />
              <stop offset="75%" stopColor="#c8956c" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#ffd899" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="bottom-left-glow" x1="0%" y1="50%" x2="50%" y2="100%">
              <stop offset="0%" stopColor="#ffd899" stopOpacity="0" />
              <stop offset="50%" stopColor="#c8956c" stopOpacity="0.8" />
              <stop offset="75%" stopColor="#ffd899" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#ffd899" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="top-left-glow" x1="0%" y1="0%" x2="50%" y2="50%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.35" />
              <stop offset="50%" stopColor="#ffd899" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#ffd899" stopOpacity="0" />
            </linearGradient>
            <filter id="glow-blur" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="soft-blur" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="6" />
            </filter>
          </defs>
          <path 
            d="M 70 35 C 150 50, 240 20, 320 35 C 355 40, 375 55, 375 100 C 375 160, 345 220, 345 270 C 345 320, 375 360, 375 400 C 375 440, 350 470, 310 475 C 230 460, 150 485, 80 470 C 45 465, 20 440, 20 395 C 20 350, 45 300, 45 250 C 45 200, 15 150, 20 100 C 20 60, 45 40, 70 35 Z"
            fill="url(#glass-radial)"
            className="opacity-95"
          />
          <path 
            d="M 70 35 C 150 50, 240 20, 320 35 C 355 40, 375 55, 375 100 C 375 160, 345 220, 345 270 C 345 320, 375 360, 375 400 C 375 440, 350 470, 310 475 C 230 460, 150 485, 80 470 C 45 465, 20 440, 20 395 C 20 350, 45 300, 45 250 C 45 200, 15 150, 20 100 C 20 60, 45 40, 70 35 Z"
            stroke="url(#gold-base)"
            strokeWidth="2.5"
            className="opacity-55"
          />
          <path 
            d="M 70 35 C 150 50, 240 20, 320 35 C 355 40, 375 55, 375 100 C 375 160, 345 220, 345 270 C 345 320, 375 360, 375 400 C 375 440, 350 470, 310 475 C 230 460, 150 485, 80 470 C 45 465, 20 440, 20 395 C 20 350, 45 300, 45 250 C 45 200, 15 150, 20 100 C 20 60, 45 40, 70 35 Z" 
            stroke="url(#top-right-glow)" 
            strokeWidth="8" 
            filter="url(#soft-blur)"
            className="opacity-70"
          />
          <path 
            d="M 70 35 C 150 50, 240 20, 320 35 C 355 40, 375 55, 375 100 C 375 160, 345 220, 345 270 C 345 320, 375 360, 375 400 C 375 440, 350 470, 310 475 C 230 460, 150 485, 80 470 C 45 465, 20 440, 20 395 C 20 350, 45 300, 45 250 C 45 200, 15 150, 20 100 C 20 60, 45 40, 70 35 Z" 
            stroke="url(#bottom-right-glow)" 
            strokeWidth="9" 
            filter="url(#soft-blur)"
            className="opacity-60"
          />
          <path 
            d="M 70 35 C 150 50, 240 20, 320 35 C 355 40, 375 55, 375 100 C 375 160, 345 220, 345 270 C 345 320, 375 360, 375 400 C 375 440, 350 470, 310 475 C 230 460, 150 485, 80 470 C 45 465, 20 440, 20 395 C 20 350, 45 300, 45 250 C 45 200, 15 150, 20 100 C 20 60, 45 40, 70 35 Z" 
            stroke="url(#bottom-left-glow)" 
            strokeWidth="9" 
            filter="url(#soft-blur)"
            className="opacity-60"
          />
          <path 
            d="M 70 35 C 150 50, 240 20, 320 35 C 355 40, 375 55, 375 100 C 375 160, 345 220, 345 270 C 345 320, 375 360, 375 400 C 375 440, 350 470, 310 475 C 230 460, 150 485, 80 470 C 45 465, 20 440, 20 395 C 20 350, 45 300, 45 250 C 45 200, 15 150, 20 100 C 20 60, 45 40, 70 35 Z" 
            stroke="url(#top-right-glow)" 
            strokeWidth="2.5" 
            filter="url(#glow-blur)"
          />
          <path 
            d="M 70 35 C 150 50, 240 20, 320 35 C 355 40, 375 55, 375 100 C 375 160, 345 220, 345 270 C 345 320, 375 360, 375 400 C 375 440, 350 470, 310 475 C 230 460, 150 485, 80 470 C 45 465, 20 440, 20 395 C 20 350, 45 300, 45 250 C 45 200, 15 150, 20 100 C 20 60, 45 40, 70 35 Z" 
            stroke="url(#bottom-right-glow)" 
            strokeWidth="2.5" 
            filter="url(#glow-blur)"
          />
          <path 
            d="M 70 35 C 150 50, 240 20, 320 35 C 355 40, 375 55, 375 100 C 375 160, 345 220, 345 270 C 345 320, 375 360, 375 400 C 375 440, 350 470, 310 475 C 230 460, 150 485, 80 470 C 45 465, 20 440, 20 395 C 20 350, 45 300, 45 250 C 45 200, 15 150, 20 100 C 20 60, 45 40, 70 35 Z" 
            stroke="url(#bottom-left-glow)" 
            strokeWidth="2.5" 
            filter="url(#glow-blur)"
          />
          <path 
            d="M 70 35 C 150 50, 240 20, 320 35 C 355 40, 375 55, 375 100 C 375 160, 345 220, 345 270 C 345 320, 375 360, 375 400 C 375 440, 350 470, 310 475 C 230 460, 150 485, 80 470 C 45 465, 20 440, 20 395 C 20 350, 45 300, 45 250 C 45 200, 15 150, 20 100 C 20 60, 45 40, 70 35 Z" 
            stroke="url(#top-left-glow)" 
            strokeWidth="1.5" 
            filter="url(#glow-blur)"
          />
          <path 
            d="M 70 35 C 150 50, 240 20, 320 35 C 355 40, 375 55, 375 100 C 375 160, 345 220, 345 270 C 345 320, 375 360, 375 400 C 375 440, 350 470, 310 475 C 230 460, 150 485, 80 470 C 45 465, 20 440, 20 395 C 20 350, 45 300, 45 250 C 45 200, 15 150, 20 100 C 20 60, 45 40, 70 35 Z"
            stroke="rgba(255, 255, 255, 0.16)"
            strokeWidth="0.75"
          />
          <path 
            d="M 285 405 C 310 425, 330 435, 350 450" 
            stroke="#ffda99" 
            strokeWidth="1.75" 
            strokeLinecap="round"
            filter="url(#glow-blur)"
            className="opacity-80"
          />
          <path 
            d="M 287 407 C 308 424, 325 433, 342 445" 
            stroke="#ffffff" 
            strokeWidth="0.75" 
            strokeLinecap="round"
            className="opacity-90"
          />
        </svg>
      </div>

      <div className="relative z-30 w-full h-full p-8 md:p-10 flex flex-col justify-center">
        {placeholderWarning && (
          <div className="mb-4 p-3 rounded-xl bg-[#f59e0b]/10 border border-[#f59e0b]/30 text-[#f59e0b] text-[10px] flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold mb-0.5">Supabase not configured</p>
              <p>Please check your environment variables.</p>
            </div>
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-[#c45a5a]/10 border border-[#c45a5a]/20 text-[#c45a5a] text-xs">
            {error}
          </div>
        )}
        {info && (
          <div className="mb-4 p-3 rounded-xl bg-[#7dac5a]/10 border border-[#7dac5a]/20 text-[#7dac5a] text-xs">
            {info}
          </div>
        )}

        <h2 className="text-center text-3xl md:text-[34px] auth-title-serif mb-8 text-[#e0e0e0] tracking-wide select-none">
          {activeTab === 'login' ? 'Sign In' : 'Sign Up'}
        </h2>

        <form onSubmit={activeTab === 'login' ? handleLogin : handleSignUp} className="space-y-5">
          <div className="space-y-1">
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[#c8956c]/70">
                <Mail className="w-4 h-4" />
              </span>
              <input
                type="email"
                required
                placeholder="Email Address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                className="w-full bg-white/[0.02] border border-[#c8956c]/25 rounded-xl pl-11 pr-4 py-3 text-sm text-[#e0e0e0] placeholder:text-[#666] focus:outline-none focus:border-[#c8956c]/80 focus:ring-1 focus:ring-[#c8956c]/20 disabled:opacity-50 transition-all auth-input-gold"
              />
            </div>
          </div>

          <div className="space-y-1">
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[#c8956c]/70">
                <Lock className="w-4 h-4" />
              </span>
              <input
                type={showPassword ? 'text' : 'password'}
                required
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                className="w-full bg-white/[0.02] border border-[#c8956c]/25 rounded-xl pl-11 pr-11 py-3 text-sm text-[#e0e0e0] placeholder:text-[#666] focus:outline-none focus:border-[#c8956c]/80 focus:ring-1 focus:ring-[#c8956c]/20 disabled:opacity-50 transition-all auth-input-gold"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-[#c8956c]/50 hover:text-[#c8956c] bg-transparent border-none cursor-pointer p-0 flex items-center justify-center"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {activeTab === 'login' && (
            <div className="flex justify-end select-none">
              <a 
                href="#forgot" 
                onClick={(e) => {
                  e.preventDefault();
                  toast.info('Password reset is not fully configured yet.');
                }}
                className="text-xs text-[#c8956c]/70 hover:text-[#c8956c] transition-all"
              >
                Forgot Password?
              </a>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 px-4 mt-2 auth-btn-gold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              activeTab === 'login' ? 'LOG IN' : 'SIGN UP'
            )}
          </button>
        </form>

        <div className="mt-8 text-center select-none">
          <p className="text-[11px] text-[#c8956c]/60 font-light mb-4">Or sign in with:</p>
          <div className="flex items-center justify-center gap-6">
            <button
              onClick={() => handleSocialLogin('google')}
              disabled={loading}
              className="auth-social-btn flex items-center justify-center w-10 h-10 rounded-full border border-[#c8956c]/20 bg-white/[0.01] hover:bg-[#c8956c]/5 transition-all"
              title="Google"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12.24 10.285V14.4h6.887c-.648 2.41-2.519 4.114-5.136 4.114-3.483 0-6.312-2.828-6.312-6.312s2.828-6.312 6.312-6.312c1.623 0 3.099.615 4.227 1.623l3.05-3.05C19.227 2.607 15.96 1.2 12.24 1.2 6.13 1.2 1.2 6.13 1.2 1.2 6.13 1.2 1.2 6.13 1.2 12.24s4.93 11.04 11.04 11.04c6.312 0 11.04-4.445 11.04-11.04 0-.748-.068-1.462-.196-2.155H12.24z" />
              </svg>
            </button>
            <button
              onClick={() => handleSocialLogin('facebook')}
              disabled={loading}
              className="auth-social-btn flex items-center justify-center w-10 h-10 rounded-full border border-[#c8956c]/20 bg-white/[0.01] hover:bg-[#c8956c]/5 transition-all"
              title="Facebook"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
              </svg>
            </button>
          </div>
        </div>

        <div className="mt-6 text-center select-none">
          <button
            onClick={() => setActiveTab(activeTab === 'login' ? 'signup' : 'login')}
            disabled={loading}
            className="text-xs text-[#c8956c]/70 hover:text-[#c8956c] transition-all bg-transparent border-none cursor-pointer"
          >
            {activeTab === 'login' ? "Don't have an account? Sign Up" : "Already have an account? Sign In"}
          </button>
        </div>
      </div>
    </div>
  )
}
