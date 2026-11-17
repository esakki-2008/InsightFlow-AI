import { useState, type FormEvent } from 'react'
import { Activity, ArrowRight, BrainCircuit, Eye, EyeOff, LockKeyhole, Mail } from 'lucide-react'
import { API_URL, type AuthResponse } from '../config/api'

interface AuthScreenProps {
  onAuthenticated: (result: AuthResponse) => void
}

export default function AuthScreen({ onAuthenticated }: AuthScreenProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      })
      const result = await response.json()
      if (!response.ok) {
        throw new Error(result.detail || (mode === 'login' ? 'Unable to sign in.' : 'Unable to create your account.'))
      }
      onAuthenticated(result as AuthResponse)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to connect to InsightFlow AI.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#09090f] px-4 py-10 text-zinc-100">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-violet-600/15 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 -right-20 h-96 w-96 rounded-full bg-indigo-600/10 blur-3xl" />
      <div className="relative grid w-full max-w-5xl overflow-hidden rounded-3xl border border-white/10 bg-[#10101a] shadow-2xl shadow-black/40 md:grid-cols-[1.05fr_0.95fr]">
        <section className="hidden flex-col justify-between border-r border-white/5 bg-gradient-to-br from-violet-600/15 via-[#11111d] to-[#11111d] p-10 md:flex">
          <div>
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-600 shadow-lg shadow-violet-600/25">
              <BrainCircuit size={26} />
            </div>
            <p className="mt-8 text-xs font-semibold tracking-[0.28em] text-violet-300">INTELLIGENT DATA ANALYST</p>
            <h1 className="mt-4 text-4xl font-bold leading-tight tracking-tight">Your data.<br />Your workspace.<br /><span className="text-violet-300">Your insights.</span></h1>
            <p className="mt-5 max-w-sm text-sm leading-7 text-zinc-400">Explore datasets, uncover patterns, train machine-learning models and turn information into decisions.</p>
          </div>
          <div className="flex items-center gap-3 text-xs text-zinc-500">
            <Activity size={16} className="text-emerald-400" />
            Private account workspace
          </div>
        </section>

        <section className="p-7 sm:p-10">
          <div className="mb-8 flex items-center gap-3 md:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600"><BrainCircuit size={22} /></div>
            <span className="font-bold">InsightFlow AI</span>
          </div>
          <div className="mb-8">
            <p className="text-sm font-medium text-violet-300">{mode === 'login' ? 'WELCOME BACK' : 'GET STARTED'}</p>
            <h2 className="mt-2 text-3xl font-bold">{mode === 'login' ? 'Sign in to your account' : 'Create your account'}</h2>
            <p className="mt-2 text-sm text-zinc-500">{mode === 'login' ? 'Continue to your personal analytics workspace.' : 'Register with your email to create a private workspace.'}</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-zinc-300">Email address</span>
              <span className="flex items-center gap-3 rounded-xl border border-white/10 bg-black/20 px-4 focus-within:border-violet-500/60">
                <Mail size={18} className="shrink-0 text-zinc-500" />
                <input type="email" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" className="h-12 w-full bg-transparent text-sm outline-none placeholder:text-zinc-600" />
              </span>
            </label>
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-zinc-300">Password</span>
              <span className="flex items-center gap-3 rounded-xl border border-white/10 bg-black/20 px-4 focus-within:border-violet-500/60">
                <LockKeyhole size={18} className="shrink-0 text-zinc-500" />
                <input type={showPassword ? 'text' : 'password'} required minLength={12} maxLength={128} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="At least 12 characters" className="h-12 w-full bg-transparent text-sm outline-none placeholder:text-zinc-600" />
                <button type="button" onClick={() => setShowPassword(v => !v)} className="text-zinc-500 hover:text-zinc-200" aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button>
              </span>
              <span className="mt-2 block text-xs text-zinc-600">Use at least 12 characters.</span>
            </label>

            {error && <div role="alert" className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

            <button type="submit" disabled={loading} className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60">
              {loading ? 'Please wait...' : mode === 'login' ? 'Sign in' : 'Create account'}
              {!loading && <ArrowRight size={17} />}
            </button>
          </form>

          <p className="mt-7 text-center text-sm text-zinc-500">
            {mode === 'login' ? "Don't have an account?" : 'Already have an account?'}{' '}
            <button type="button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }} className="font-semibold text-violet-300 hover:text-violet-200">
              {mode === 'login' ? 'Create one' : 'Sign in'}
            </button>
          </p>
          <p className="mt-8 text-center text-xs leading-5 text-zinc-600">Your account gives you a separate workspace. Never share your password or access token.</p>
        </section>
      </div>
    </main>
  )
}
