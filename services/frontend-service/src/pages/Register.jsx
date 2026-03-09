import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import { Spinner } from '../components/ui/Spinner'
import { Zap } from 'lucide-react'
import toast from 'react-hot-toast'

export function Register() {
  const { register, login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', username: '', full_name: '', password: '' })
  const [loading, setLoading] = useState(false)

  const set = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }))

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await register(form)
      await login(form.email, form.password)
      toast.success('Account created!')
      navigate('/')
    } catch (err) {
      toast.error(err?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute inset-0 opacity-[0.03]"
        style={{ backgroundImage: 'linear-gradient(#00ff9d 1px, transparent 1px), linear-gradient(90deg, #00ff9d 1px, transparent 1px)', backgroundSize: '40px 40px' }} />

      <div className="w-full max-w-sm animate-slide-up relative z-10">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-forge-accent/10 border border-forge-accent/20 mb-4">
            <Zap size={26} className="text-forge-accent" fill="currentColor" />
          </div>
          <h1 className="font-display font-bold text-3xl text-forge-text">Create account</h1>
          <p className="text-forge-text-3 text-sm mt-1">Join TaskForge today</p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-4">
          {[
            { key: 'full_name', label: 'Full Name',  type: 'text',     placeholder: 'Jane Smith' },
            { key: 'username',  label: 'Username',   type: 'text',     placeholder: 'janesmith' },
            { key: 'email',     label: 'Email',      type: 'email',    placeholder: 'jane@example.com' },
            { key: 'password',  label: 'Password',   type: 'password', placeholder: 'Min 8 chars, 1 uppercase, 1 number' },
          ].map(({ key, label, type, placeholder }) => (
            <div key={key}>
              <label className="block text-xs font-mono text-forge-text-3 mb-1.5 uppercase tracking-wider">{label}</label>
              <input className="input" type={type} placeholder={placeholder} value={form[key]} onChange={set(key)} required />
            </div>
          ))}

          <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
            {loading ? <Spinner size="sm" className="mx-auto" /> : 'Create account'}
          </button>
        </form>

        <p className="text-center text-forge-text-3 text-sm mt-5">
          Already have an account?{' '}
          <Link to="/login" className="text-forge-accent hover:text-forge-accent-dim transition-colors font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
