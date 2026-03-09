import { useState } from 'react'
import { useAuth } from '../hooks/useAuth.jsx'
import { authApi } from '../api/auth'
import { Spinner } from '../components/ui/Spinner'
import { User, Lock, Save, Shield } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import toast from 'react-hot-toast'

export function Profile() {
  const { user, refreshUser } = useAuth()
  const [profileLoading, setProfileLoading] = useState(false)
  const [pwLoading, setPwLoading]           = useState(false)

  const [profile, setProfile] = useState({
    full_name:  user?.full_name  || '',
    bio:        user?.bio        || '',
    avatar_url: user?.avatar_url || '',
  })

  const [pw, setPw] = useState({
    current_password: '', new_password: '', confirm: ''
  })

  async function saveProfile(e) {
    e.preventDefault()
    setProfileLoading(true)
    try {
      await authApi.update(profile)
      await refreshUser()
      toast.success('Profile updated')
    } catch (e) {
      toast.error(e?.detail || 'Failed to update profile')
    } finally {
      setProfileLoading(false)
    }
  }

  async function changePassword(e) {
    e.preventDefault()
    if (pw.new_password !== pw.confirm) {
      toast.error('Passwords do not match')
      return
    }
    setPwLoading(true)
    try {
      await authApi.changePassword({
        current_password: pw.current_password,
        new_password:     pw.new_password,
      })
      setPw({ current_password: '', new_password: '', confirm: '' })
      toast.success('Password changed')
    } catch (e) {
      toast.error(e?.detail || 'Failed to change password')
    } finally {
      setPwLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display font-bold text-2xl text-forge-text">Profile</h1>
        <p className="text-forge-text-3 text-sm mt-0.5">Manage your account settings</p>
      </div>

      {/* Account info card */}
      <div className="card flex items-center gap-4">
        <div className="w-14 h-14 rounded-2xl bg-forge-accent/10 border border-forge-accent/20
          flex items-center justify-center shrink-0">
          <span className="font-display font-bold text-xl text-forge-accent">
            {(user?.full_name || user?.username || '?')[0].toUpperCase()}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-display font-semibold text-forge-text">{user?.full_name || user?.username}</p>
          <p className="text-forge-text-3 text-sm font-mono">{user?.email}</p>
          <div className="flex items-center gap-3 mt-1.5">
            <span className="badge bg-forge-accent/10 text-forge-accent">@{user?.username}</span>
            {user?.is_verified && (
              <span className="flex items-center gap-1 text-[10px] font-mono text-forge-info">
                <Shield size={10} /> verified
              </span>
            )}
            {user?.created_at && (
              <span className="text-[10px] font-mono text-forge-text-3">
                Joined {format(parseISO(user.created_at), 'MMM yyyy')}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Edit profile */}
      <div className="card">
        <div className="flex items-center gap-2.5 mb-5">
          <div className="p-2 rounded-lg bg-forge-muted/50">
            <User size={15} className="text-forge-text-2" />
          </div>
          <h2 className="font-display font-semibold text-forge-text">Edit Profile</h2>
        </div>
        <form onSubmit={saveProfile} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-forge-text-3 mb-1.5 uppercase tracking-wider">Full Name</label>
            <input className="input" value={profile.full_name}
              onChange={e => setProfile(p => ({ ...p, full_name: e.target.value }))}
              placeholder="Your full name" />
          </div>
          <div>
            <label className="block text-xs font-mono text-forge-text-3 mb-1.5 uppercase tracking-wider">Bio</label>
            <textarea className="input resize-none h-20" value={profile.bio}
              onChange={e => setProfile(p => ({ ...p, bio: e.target.value }))}
              placeholder="A short bio..." />
          </div>
          <div>
            <label className="block text-xs font-mono text-forge-text-3 mb-1.5 uppercase tracking-wider">Avatar URL</label>
            <input className="input font-mono text-sm" value={profile.avatar_url}
              onChange={e => setProfile(p => ({ ...p, avatar_url: e.target.value }))}
              placeholder="https://example.com/avatar.png" />
          </div>
          <button type="submit" disabled={profileLoading} className="btn-primary flex items-center gap-2">
            {profileLoading ? <Spinner size="sm" /> : <Save size={14} />}
            Save Changes
          </button>
        </form>
      </div>

      {/* Change password */}
      <div className="card">
        <div className="flex items-center gap-2.5 mb-5">
          <div className="p-2 rounded-lg bg-forge-muted/50">
            <Lock size={15} className="text-forge-text-2" />
          </div>
          <h2 className="font-display font-semibold text-forge-text">Change Password</h2>
        </div>
        <form onSubmit={changePassword} className="space-y-4">
          {[
            { key: 'current_password', label: 'Current Password' },
            { key: 'new_password',     label: 'New Password' },
            { key: 'confirm',          label: 'Confirm New Password' },
          ].map(({ key, label }) => (
            <div key={key}>
              <label className="block text-xs font-mono text-forge-text-3 mb-1.5 uppercase tracking-wider">{label}</label>
              <input className="input" type="password" required
                value={pw[key]} onChange={e => setPw(p => ({ ...p, [key]: e.target.value }))}
                placeholder="••••••••" />
            </div>
          ))}
          <button type="submit" disabled={pwLoading} className="btn-primary flex items-center gap-2">
            {pwLoading ? <Spinner size="sm" /> : <Lock size={14} />}
            Update Password
          </button>
        </form>
      </div>
    </div>
  )
}
