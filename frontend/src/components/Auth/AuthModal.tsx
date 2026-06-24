import React, { useState } from 'react'
import { supabase } from '../../lib/supabase'

type AuthModalProps = {
  opened?: boolean
  onClose?: () => void
}

export const AuthModal: React.FC<AuthModalProps> = ({ opened = true, onClose }) => {
  const [activeTab, setActiveTab] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) throw error
      onClose?.()
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setInfo(null)
    try {
      const { data, error } = await supabase.auth.signUp({ email, password })
      if (error) throw error
      if (data.session) {
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Background */}
      <div className="absolute inset-0 bg-black/80" />

      {/* Modal */}
      <div className="relative w-full max-w-md mx-4 liquid-glass-strong rounded-2xl p-6">
        {/* Header */}
        <div className="text-center mb-6">
          <h2 className="text-xl font-bold text-[#e0e0e0]">
            {activeTab === 'login' ? 'Sign In to Deep Research Agent' : 'Create an Account'}
          </h2>
        </div>

        {/* Notifications */}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-[#c45a5a]/10 border border-[#c45a5a]/20 text-[#c45a5a] text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-[#c45a5a] hover:text-[#e0e0e0] cursor-pointer bg-transparent border-none">✕</button>
          </div>
        )}
        {info && (
          <div className="mb-4 p-3 rounded-lg bg-[#7dac5a]/10 border border-[#7dac5a]/20 text-[#7dac5a] text-sm flex items-center justify-between">
            <span>{info}</span>
            <button onClick={() => setInfo(null)} className="text-[#7dac5a] hover:text-[#e0e0e0] cursor-pointer bg-transparent border-none">✕</button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex bg-white/[0.03] rounded-xl p-0.5 mb-6">
          {(['login', 'signup'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-150 cursor-pointer border-none ${
                activeTab === tab
                  ? 'bg-white/[0.06] text-[#e0e0e0]'
                  : 'text-[#555] hover:text-[#999]'
              }`}
            >
              {tab === 'login' ? 'Sign In' : 'Sign Up'}
            </button>
          ))}
        </div>

        {/* Login Form */}
        {activeTab === 'login' && (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs uppercase tracking-wider text-[#555] font-semibold mb-2">Email address</label>
              <input
                type="email"
                required
                placeholder="hello@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-2.5 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:outline-none focus:border-[#c8956c]/50 disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-[#555] font-semibold mb-2">Password</label>
              <input
                type="password"
                required
                placeholder="Your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-2.5 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:outline-none focus:border-[#c8956c]/50 disabled:opacity-50"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl text-sm font-medium bg-[#c8956c]/15 text-[#c8956c] hover:bg-[#c8956c]/25 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150 cursor-pointer border-none"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        )}

        {/* Signup Form */}
        {activeTab === 'signup' && (
          <form onSubmit={handleSignUp} className="space-y-4">
            <div>
              <label className="block text-xs uppercase tracking-wider text-[#555] font-semibold mb-2">Email address</label>
              <input
                type="email"
                required
                placeholder="hello@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-2.5 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:outline-none focus:border-[#c8956c]/50 disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wider text-[#555] font-semibold mb-2">Password</label>
              <input
                type="password"
                required
                placeholder="Min 6 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl px-4 py-2.5 text-sm text-[#e0e0e0] placeholder:text-[#555] focus:outline-none focus:border-[#c8956c]/50 disabled:opacity-50"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl text-sm font-medium bg-[#c8956c]/15 text-[#c8956c] hover:bg-[#c8956c]/25 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150 cursor-pointer border-none"
            >
              {loading ? 'Creating account...' : 'Sign Up'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
