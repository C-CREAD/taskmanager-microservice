import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { analyticsApi } from '../api/analytics'
import { useAuth } from '../hooks/useAuth.jsx'
import { Spinner } from '../components/ui/Spinner'
import {
  CheckSquare, Clock, AlertTriangle, Flame,
  TrendingUp, Target, Zap, ArrowRight, Calendar
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid
} from 'recharts'
import { format, parseISO } from 'date-fns'

function StatCard({ icon: Icon, label, value, sub, accent = false }) {
  return (
    <div className={`stat-card ${accent ? 'border-forge-accent/30 bg-forge-accent/5' : ''}`}>
      <div className="flex items-start justify-between">
        <div className={`p-2 rounded-lg ${accent ? 'bg-forge-accent/15' : 'bg-forge-muted/60'}`}>
          <Icon size={16} className={accent ? 'text-forge-accent' : 'text-forge-text-2'} />
        </div>
      </div>
      <div className="mt-3">
        <p className={`font-display font-bold text-2xl ${accent ? 'text-forge-accent' : 'text-forge-text'}`}>{value}</p>
        <p className="text-xs font-mono text-forge-text-3 mt-0.5 uppercase tracking-wider">{label}</p>
        {sub && <p className="text-xs text-forge-text-3 mt-1">{sub}</p>}
      </div>
    </div>
  )
}

function ScoreRing({ score }) {
  const radius = 36
  const circ   = 2 * Math.PI * radius
  const offset = circ - (score / 100) * circ
  const color  = score >= 70 ? '#00ff9d' : score >= 40 ? '#ff7b3a' : '#ff3a5c'

  return (
    <div className="relative w-24 h-24 flex items-center justify-center">
      <svg className="absolute inset-0 -rotate-90" width="96" height="96">
        <circle cx="48" cy="48" r={radius} fill="none" stroke="#1e1e2e" strokeWidth="6" />
        <circle cx="48" cy="48" r={radius} fill="none" stroke={color} strokeWidth="6"
          strokeDasharray={circ} strokeDashoffset={offset}
          strokeLinecap="round" style={{ transition: 'stroke-dashoffset 1s ease' }} />
      </svg>
      <div className="relative text-center">
        <p className="font-display font-bold text-xl" style={{ color }}>{score}</p>
        <p className="font-mono text-[9px] text-forge-text-3 uppercase">Score</p>
      </div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-forge-surface border border-forge-border rounded-lg px-3 py-2 text-xs">
      <p className="font-mono text-forge-text-3 mb-1">{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color }} className="font-medium">
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  )
}

export function Dashboard() {
  const { user } = useAuth()
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    analyticsApi.dashboard()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen">
      <Spinner size="lg" />
    </div>
  )

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  const trendData = (data?.daily_trend || []).slice(-14).map(d => ({
    date: format(parseISO(d.date), 'MMM d'),
    Completed: d.completed,
    Created: d.created,
  }))

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6 animate-fade-in">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-forge-text-3 font-mono text-xs uppercase tracking-widest mb-1">{greeting}</p>
          <h1 className="font-display font-bold text-2xl text-forge-text">
            {user?.full_name || user?.username}
          </h1>
          <p className="text-forge-text-3 text-sm mt-1">
            {format(new Date(), 'EEEE, MMMM d')}
          </p>
        </div>
        <Link to="/tasks" className="btn-primary flex items-center gap-2">
          <Zap size={14} />
          New Task
        </Link>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={CheckSquare} label="Total Tasks"  value={data?.summary?.total_tasks ?? 0} />
        <StatCard icon={Target}      label="Completed"    value={data?.summary?.completed ?? 0} accent />
        <StatCard icon={Clock}       label="Due Today"    value={data?.summary?.due_today ?? 0}
          sub={data?.summary?.in_progress ? `${data.summary.in_progress} in progress` : null} />
        <StatCard icon={AlertTriangle} label="Overdue"   value={data?.summary?.overdue ?? 0}
          sub={data?.summary?.completed_today ? `${data.summary.completed_today} done today` : null} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Trend chart */}
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold text-forge-text">Activity — Last 14 Days</h2>
            <TrendingUp size={16} className="text-forge-text-3" />
          </div>
          {trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={trendData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradCompleted" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#00ff9d" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#00ff9d" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradCreated" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#4d9fff" stopOpacity={0.1} />
                    <stop offset="95%" stopColor="#4d9fff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#55556a', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#55556a', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="Completed" stroke="#00ff9d" strokeWidth={2} fill="url(#gradCompleted)" dot={false} />
                <Area type="monotone" dataKey="Created"   stroke="#4d9fff" strokeWidth={2} fill="url(#gradCreated)"   dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[180px] flex items-center justify-center text-forge-text-3 text-sm">
              No activity data yet
            </div>
          )}
        </div>

        {/* Productivity score */}
        <div className="card flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold text-forge-text">Productivity</h2>
            <Flame size={16} className="text-forge-warn" />
          </div>

          <div className="flex items-center gap-5 mb-5">
            <ScoreRing score={data?.productivity?.score ?? 0} />
            <div className="space-y-2">
              <div>
                <p className="font-mono text-[10px] text-forge-text-3 uppercase">Streak</p>
                <p className="font-display font-bold text-lg text-forge-warn">
                  {data?.productivity?.streak_days ?? 0}d
                </p>
              </div>
              <div>
                <p className="font-mono text-[10px] text-forge-text-3 uppercase">Avg / Day</p>
                <p className="font-display font-bold text-lg text-forge-info">
                  {data?.productivity?.avg_tasks_per_day ?? 0}
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-2.5 mt-auto">
            {[
              { label: 'Completion', value: data?.rates?.completion_pct ?? 0, color: '#00ff9d' },
              { label: 'On-time',    value: data?.rates?.on_time_pct ?? 0,    color: '#4d9fff' },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-mono text-forge-text-3">{label}</span>
                  <span className="font-mono font-medium" style={{ color }}>{value}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-forge-muted overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-1000"
                    style={{ width: `${value}%`, backgroundColor: color }} />
                </div>
              </div>
            ))}
          </div>

          <Link to="/analytics" className="flex items-center gap-1.5 text-xs text-forge-text-3 hover:text-forge-accent mt-4 transition-colors group">
            <span>Full analytics</span>
            <ArrowRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>
      </div>

      {/* Status breakdown */}
      {data?.by_status && (
        <div className="card">
          <h2 className="font-display font-semibold text-forge-text mb-4">Tasks by Status</h2>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {Object.entries(data.by_status).map(([status, count]) => (
              <Link key={status} to={`/tasks?status=${status}`}
                className="flex flex-col items-center gap-1.5 p-3 rounded-lg bg-forge-muted/30
                           border border-forge-border hover:border-forge-muted transition-colors">
                <span className={`badge-${status} text-center`}>{status.replace('_', ' ')}</span>
                <span className="font-display font-bold text-xl text-forge-text">{count}</span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
