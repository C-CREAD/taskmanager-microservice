import { Outlet } from 'react-router-dom'
import { useState, useCallback, useEffect } from 'react'
import { Sidebar } from './Sidebar'
import { useWebSocket } from '../../hooks/useWebSocket.jsx'
import { notifApi } from '../../api/notifications'
import toast from 'react-hot-toast'
import { Bell } from 'lucide-react'

export function AppLayout() {
  const [unreadCount, setUnreadCount] = useState(0)

  // Load initial unread count
  useEffect(() => {
    notifApi.unreadCount()
      .then(d => setUnreadCount(d.unread_count))
      .catch(() => {})
  }, [])

  const handleNotification = useCallback((data) => {
    setUnreadCount(c => c + 1)
    toast.custom((t) => (
      <div className={`${t.visible ? 'animate-slide-up' : 'opacity-0'}
        flex items-start gap-3 bg-forge-surface border border-forge-accent/30
        rounded-xl px-4 py-3 shadow-2xl max-w-sm`}>
        <div className="w-8 h-8 rounded-lg bg-forge-accent/15 flex items-center justify-center shrink-0 mt-0.5">
          <Bell size={14} className="text-forge-accent" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-display font-semibold text-forge-text">{data.title}</p>
          <p className="text-xs text-forge-text-2 mt-0.5 truncate">{data.body}</p>
        </div>
      </div>
    ), { duration: 4000 })
  }, [])

  useWebSocket(handleNotification)

  return (
    <div className="flex min-h-screen">
      <Sidebar unreadCount={unreadCount} />
      <main className="flex-1 min-w-0 overflow-auto">
        <Outlet context={{ unreadCount, setUnreadCount }} />
      </main>
    </div>
  )
}
