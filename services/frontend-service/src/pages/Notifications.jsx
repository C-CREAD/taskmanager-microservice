import { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { notifApi } from '../api/notifications'
import { Spinner } from '../components/ui/Spinner'
import { Empty } from '../components/ui/Empty'
import {
  Bell, CheckCheck, CheckSquare, Clock,
  AlertTriangle, Info, Circle
} from 'lucide-react'
import { formatDistanceToNow, parseISO } from 'date-fns'
import toast from 'react-hot-toast'

const TYPE_CONFIG = {
  task_created:   { icon: CheckSquare, color: 'text-forge-accent',  bg: 'bg-forge-accent/10'  },
  task_assigned:  { icon: Circle,      color: 'text-forge-info',    bg: 'bg-forge-info/10'    },
  task_completed: { icon: CheckCheck,  color: 'text-forge-accent',  bg: 'bg-forge-accent/10'  },
  task_due_soon:  { icon: Clock,       color: 'text-forge-warn',    bg: 'bg-forge-warn/10'    },
  task_overdue:   { icon: AlertTriangle,color: 'text-forge-danger', bg: 'bg-forge-danger/10'  },
  system:         { icon: Info,        color: 'text-forge-text-2',  bg: 'bg-forge-muted/50'   },
}

function NotifItem({ notif, onRead }) {
  const cfg = TYPE_CONFIG[notif.type] || TYPE_CONFIG.system
  const Icon = cfg.icon

  async function handleRead() {
    if (notif.is_read) return
    try {
      await notifApi.markRead(notif.id)
      onRead(notif.id)
    } catch {}
  }

  return (
    <div onClick={handleRead}
      className={`flex items-start gap-4 px-5 py-4 border-b border-forge-border
        transition-all duration-200 cursor-pointer
        ${notif.is_read ? 'opacity-60' : 'hover:bg-forge-muted/20'}`}>

      <div className={`${cfg.bg} p-2.5 rounded-xl shrink-0 mt-0.5`}>
        <Icon size={15} className={cfg.color} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-3">
          <p className={`text-sm font-body font-medium ${notif.is_read ? 'text-forge-text-2' : 'text-forge-text'}`}>
            {notif.title}
          </p>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px] font-mono text-forge-text-3">
              {formatDistanceToNow(parseISO(notif.created_at), { addSuffix: true })}
            </span>
            {!notif.is_read && (
              <div className="w-2 h-2 rounded-full bg-forge-accent shrink-0" />
            )}
          </div>
        </div>
        {notif.body && (
          <p className="text-xs text-forge-text-3 mt-0.5 line-clamp-2">{notif.body}</p>
        )}
        <span className="inline-block mt-1.5 text-[10px] font-mono text-forge-text-3 uppercase tracking-wider">
          {notif.type?.replace(/_/g, ' ')}
        </span>
      </div>
    </div>
  )
}

export function Notifications() {
  const ctx = useOutletContext()
  const [notifs, setNotifs]     = useState([])
  const [loading, setLoading]   = useState(true)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [page, setPage]         = useState(1)
  const [hasMore, setHasMore]   = useState(false)

  async function fetchNotifs(p = 1, unread = unreadOnly, replace = true) {
    try {
      const data = await notifApi.list({
        page: p, page_size: 25,
        ...(unread ? { unread_only: true } : {})
      })
      const results = data.results || []
      setNotifs(prev => replace ? results : [...prev, ...results])
      setHasMore(!!data.next)
      setPage(p)
    } catch {
      toast.error('Failed to load notifications')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchNotifs(1, unreadOnly, true) }, [unreadOnly])

  async function markAllRead() {
    try {
      await notifApi.markAllRead()
      setNotifs(p => p.map(n => ({ ...n, is_read: true })))
      ctx?.setUnreadCount?.(0)
      toast.success('All marked as read')
    } catch {
      toast.error('Failed')
    }
  }

  function handleRead(id) {
    setNotifs(p => p.map(n => n.id === id ? { ...n, is_read: true } : n))
    ctx?.setUnreadCount?.(c => Math.max(0, c - 1))
  }

  const unreadCount = notifs.filter(n => !n.is_read).length

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-5 animate-fade-in">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-2xl text-forge-text flex items-center gap-2">
            Notifications
            {unreadCount > 0 && (
              <span className="badge bg-forge-accent/15 text-forge-accent font-mono">
                {unreadCount} new
              </span>
            )}
          </h1>
          <p className="text-forge-text-3 text-sm mt-0.5">Your activity feed</p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-forge-text-2 cursor-pointer">
            <input type="checkbox" checked={unreadOnly} onChange={e => setUnreadOnly(e.target.checked)}
              className="accent-forge-accent" />
            Unread only
          </label>
          {unreadCount > 0 && (
            <button onClick={markAllRead} className="btn-ghost flex items-center gap-2 text-xs">
              <CheckCheck size={14} />
              Mark all read
            </button>
          )}
        </div>
      </div>

      {/* List */}
      <div className="card p-0 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16"><Spinner /></div>
        ) : notifs.length === 0 ? (
          <Empty icon={Bell} title="All caught up"
            description={unreadOnly ? 'No unread notifications' : 'Notifications will appear here'} />
        ) : (
          <>
            {notifs.map(n => (
              <NotifItem key={n.id} notif={n} onRead={handleRead} />
            ))}
            {hasMore && (
              <div className="p-4 text-center">
                <button onClick={() => fetchNotifs(page + 1, unreadOnly, false)}
                  className="btn-ghost text-xs">
                  Load more
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
