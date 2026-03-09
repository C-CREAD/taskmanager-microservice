import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, CheckSquare, Bell, BarChart3,
  LogOut, User, Zap, Circle
} from 'lucide-react'
import { useAuth } from '../../hooks/useAuth.jsx'
import toast from 'react-hot-toast'

const NAV = [
  { to: '/',              icon: LayoutDashboard, label: 'Dashboard'     },
  { to: '/tasks',         icon: CheckSquare,     label: 'Tasks'         },
  { to: '/notifications', icon: Bell,            label: 'Notifications' },
  { to: '/analytics',     icon: BarChart3,       label: 'Analytics'     },
]

export function Sidebar({ unreadCount = 0 }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    toast.success('Signed out')
    navigate('/login')
  }

  return (
    <aside className="w-60 min-h-screen bg-forge-surface border-r border-forge-border flex flex-col shrink-0">

      {/* Logo */}
      <div className="px-5 py-6 border-b border-forge-border">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-forge-accent flex items-center justify-center shrink-0">
            <Zap size={14} className="text-forge-bg" fill="currentColor" />
          </div>
          <span className="font-display font-bold text-forge-text tracking-tight text-lg animate-glow">
            TaskForge
          </span>
        </div>
        <p className="text-forge-text-3 font-mono text-xs mt-1.5 ml-9">v1.0.0</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              isActive ? 'nav-item-active flex' : 'nav-item flex'
            }
          >
            <Icon size={16} className="shrink-0" />
            <span className="flex-1">{label}</span>
            {label === 'Notifications' && unreadCount > 0 && (
              <span className="min-w-[18px] h-[18px] rounded-full bg-forge-accent text-forge-bg
                               text-[10px] font-mono font-bold flex items-center justify-center px-1">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="px-3 py-4 border-t border-forge-border space-y-0.5">
        <NavLink to="/profile"
          className={({ isActive }) => isActive ? 'nav-item-active flex' : 'nav-item flex'}>
          <User size={16} className="shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-forge-text truncate">
              {user?.full_name || user?.username}
            </p>
            <p className="text-[10px] font-mono text-forge-text-3 truncate">{user?.email}</p>
          </div>
          <Circle size={8} className="text-forge-accent fill-forge-accent shrink-0 mt-0.5" />
        </NavLink>

        <button onClick={handleLogout} className="nav-item w-full text-left text-forge-danger hover:bg-forge-danger/10 hover:text-forge-danger">
          <LogOut size={16} className="shrink-0" />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  )
}
