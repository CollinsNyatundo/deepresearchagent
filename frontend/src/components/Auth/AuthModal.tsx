import React, { useState } from 'react'
import { supabase } from '../../lib/supabase'
import { Mail, Lock, Eye, EyeOff, AlertTriangle } from 'lucide-react'
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
      setError('Supabase not configured. Please set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in your .env file.')
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
      setError('Supabase not configured. Please set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in your .env file.')
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

  if (!opened) return null

  const placeholderWarning = isPlaceholderConfig()

  return (
    <div className="w-full max-w-sm mx-auto">
      {/* Title */}
      <h2 className="text-3xl font-light text-center text-[#e0e0e0] mb-8 tracking-wide">
        {activeTab === 'login' ? 'Sign In' : 'Sign Up'}
      </h2>

      {/* Placeholder config warning */}
      {placeholderWarning && (
        <div className="mb-4 p-3 rounded-xl bg-[#f59e0b]/10 border border-[#f59e0b]/30 text-[#f59e0b] text-xs flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold mb-0.5">Supabase not configured</p>
            <p>Set <code className="bg-white/[0.1] px-1 rounded">VITE_SUPABASE_URL</code> and <code className="bg-white/[0.1] px-1 rounded">VITE_SUPABASE_ANON_KEY</code> in your <code className="bg-white/[0.1] px-1 rounded">.env</code></p>
          </div>
        </div>
      )}

      {/* Error / Info */}
      {error && (
        <div className="mb-4 p-3 rounded-xl bg-[#c45a5a]/10 border border-[#c45a5a]/20 text-[#c45a5a] text-sm text-center">
          {error}
        </div>
      )}
      {info && (
        <div className="mb-4 p-3 rounded-xl bg-[#7dac5a]/10 border border-[#7dac5a]/20 text-[#7dac5a] text-sm text-center">
          {info}
        </div>
      )}

      {/* Login Form */}
      {activeTab === 'login' && (
        <form onSubmit={handleLogin} className="space-y-4">
          {/* Email */}
          <div className="relative">
            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#555]" />
            <input
              type="email"
              required
              placeholder="Email Address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              className="w-full bg-transparent border border-white/[0.08] rounded-xl pl-10 pr-4 py-3 text-sm text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#c8956c]/40 transition-all"
            />
          </div>

          {/* Password */}
          <div className="relative">
            <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#555]" />
            <input
              type={showPassword ? 'text' : 'password'}
              required
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              className="w-full bg-transparent border border-white/[0.08] rounded-xl pl-10 pr-10 py-3 text-sm text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#c8956c]/40 transition-all"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#555] hover:text-[#999] bg-transparent border-none cursor-pointer"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>

          {/* Forgot Password */}
          <div className="text-right">
            <button
              type="button"
              className="text-xs text-[#c8956c]/70 hover:text-[#c8956c] bg-transparent border-none cursor-pointer transition-colors"
            >
              Forgot Password?
            </button>
          </div>

          {/* Login Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-full text-sm font-medium tracking-wider uppercase border border-white/[0.12] bg-white/[0.03] text-[#c8956c] hover:bg-white/[0.06] hover:border-[#c8956c]/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 cursor-pointer"
          >
            {loading ? 'Signing in...' : 'Log In'}
          </button>
        </form>
      )}

      {/* Signup Form */}
      {activeTab === 'signup' && (
        <form onSubmit={handleSignUp} className="space-y-4">
          <div className="relative">
            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#555]" />
            <input
              type="email"
              required
              placeholder="Email Address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              className="w-full bg-transparent border border-white/[0.08] rounded-xl pl-10 pr-4 py-3 text-sm text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#c8956c]/40 transition-all"
            />
          </div>
          <div className="relative">
            <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#555]" />
            <input
              type={showPassword ? 'text' : 'password'}
              required
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              className="w-full bg-transparent border border-white/[0.08] rounded-xl pl-10 pr-10 py-3 text-sm text-[#e0e0e0] placeholder:text-[#444] focus:outline-none focus:border-[#c8956c]/40 transition-all"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#555] hover:text-[#999] bg-transparent border-none cursor-pointer"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-full text-sm font-medium tracking-wider uppercase border border-white/[0.12] bg-white/[0.03] text-[#c8956c] hover:bg-white/[0.06] hover:border-[#c8956c]/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 cursor-pointer"
          >
            {loading ? 'Creating account...' : 'Sign Up'}
          </button>
        </form>
      )}

      {/* Divider */}
      <div className="mt-6 mb-4 flex items-center gap-3">
        <div className="flex-1 h-px bg-white/[0.06]" />
        <span className="text-[10px] text-[#444] uppercase tracking-wider">Or sign in with</span>
        <div className="flex-1 h-px bg-white/[0.06]" />
      </div>

      {/* Social Icons */}
      <div className="flex justify-center gap-4">
        {/* Google */}
        <button className="w-10 h-10 rounded-full border border-white/[0.08] bg-white/[0.03] flex items-center justify-center text-[#c8956c] hover:bg-white/[0.06] hover:border-[#c8956c]/20 transition-all cursor-pointer">
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.84z"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
        </button>
        {/* Apple */}
        <button className="w-10 h-10 rounded-full border border-white/[0.08] bg-white/[0.03] flex items-center justify-center text-[#c8956c] hover:bg-white/[0.06] hover:border-[#c8956c]/20 transition-all cursor-pointer">
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
          </svg>
        </button>
        {/* Facebook */}
        <button className="w-10 h-10 rounded-full border border-white/[0.08] bg-white/[0.03] flex items-center justify-center text-[#c8956c] hover:bg-white/[0.06] hover:border-[#c8956c]/20 transition-all cursor-pointer">
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
          </svg>
        </button>
      </div>

      {/* Bottom Toggle */}
      <div className="mt-6 text-center">
        <span className="text-xs text-[#555]">
          {activeTab === 'login' ? "Don't have an account? " : "Already have an account? "}
        </span>
        <button
          type="button"
          onClick={() => { setActiveTab(activeTab === 'login' ? 'signup' : 'login'); setError(null); setInfo(null); }}
          className="text-xs text-[#c8956c] hover:text-[#d4a87a] bg-transparent border-none cursor-pointer transition-colors"
        >
          {activeTab === 'login' ? 'Sign Up' : 'Log In'}
        </button>
      </div>
    </div>
  )
}
