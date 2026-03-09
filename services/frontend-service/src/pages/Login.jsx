import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import { Spinner } from '../components/ui/Spinner'
import { Zap, Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'

export function Login() {
  const { login } = useAuth()
  const navigate   = useNavigate()
  const [form, setForm]       = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const [showPw, setShowPw]   = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await login(form.email, form.password)
      toast.success('Welcome back!')
      navigate('/')
    } catch (err) {
      toast.error(err?.detail || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      {/*/!* Background grid *!/*/}
      {/*<div className="absolute inset-0 opacity-[0.03]"*/}
      {/*  style={{ backgroundImage: 'linear-gradient(#00ff9d 1px, transparent 1px), linear-gradient(90deg, #00ff9d 1px, transparent 1px)', backgroundSize: '40px 40px' }} />*/}

      <div className="w-full max-w-sm animate-slide-up relative z-10">
        {/* Logo */}
        <div className="text-center mb-10">
          {/*<div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-forge-accent/10 border border-forge-accent/20 mb-4">*/}
          {/*  <Zap size={26} className="text-forge-accent" fill="currentColor" />*/}
          {/*</div>*/}
          <h1 className="font-display font-bold text-3xl text-forge-text animate-glow">TaskForge</h1>
          <p className="text-forge-text-3 text-sm mt-1 font-body">Sign in to your workspace</p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-4">
          <div>
            <label className="block text-xs font-mono text-forge-text-3 mb-1.5 uppercase tracking-wider">Email</label>
            <input
              className="input"
              type="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-forge-text-3 mb-1.5 uppercase tracking-wider">Password</label>
            <div className="relative">
              <input
                className="input pr-10"
                type={showPw ? 'text' : 'password'}
                placeholder="••••••••"
                value={form.password}
                onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                required
              />
              <button type="button" onClick={() => setShowPw(p => !p)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-forge-text-3 hover:text-forge-text-2 transition-colors">
                {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
            {loading ? <Spinner size="sm" className="mx-auto" /> : 'Sign in'}
          </button>
        </form>

        <p className="text-center text-forge-text-3 text-sm mt-5">
          No account?{' '}
          <Link to="/register" className="text-forge-accent hover:text-forge-accent-dim transition-colors font-medium">
            Create one
          </Link>
        </p>
      </div>
    </div>
  )
}
