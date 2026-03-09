import { useEffect, useState } from 'react'
import { analyticsApi } from '../api/analytics'
import { Spinner } from '../components/ui/Spinner'
import { RefreshCw, Download, TrendingUp, Award, Flame } from 'lucide-react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell, Legend
} from 'recharts'
import { format, parseISO } from 'date-fns'
import toast from 'react-hot-toast'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-forge-surface border border-forge-border rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="font-mono text-forge-text-3 mb-1.5">{label}</p>
      {payload.map(p => (
        <p key={p.name} className="font-medium" style={{ color: p.color }}>
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  )
}

function Heatmap({ data }) {
  if (!data?.length) return null
  const max = Math.max(...data.map(d => d.count), 1)

  function getColor(count) {
    if (count === 0) return '#1e1e2e'
    const intensity = count / max
    if (intensity < 0.25) return '#00ff9d20'
    if (intensity < 0.5)  return '#00ff9d50'
    if (intensity < 0.75) return '#00ff9d90'
    return '#00ff9d'
  }

  // Group by week
  const weeks = []
  let week = []
  data.forEach((d, i) => {
    week.push(d)
    if (d.weekday === 6 || i === data.length - 1) {
      weeks.push(week)
      week = []
    }
  })

  return (
    <div className="overflow-x-auto">
      <div className="flex gap-0.5 min-w-max">
        {weeks.map((w, wi) => (
          <div key={wi} className="flex flex-col gap-0.5">
            {w.map(d => (
              <div key={d.date}
                title={`${d.date}: ${d.count} task${d.count !== 1 ? 's' : ''}`}
                className="w-3 h-3 rounded-sm transition-all duration-200 hover:ring-1 hover:ring-forge-accent/40 cursor-default"
                style={{ backgroundColor: getColor(d.count) }}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-1.5 mt-3">
        <span className="text-[10px] font-mono text-forge-text-3">Less</span>
        {[0, 0.25, 0.5, 0.75, 1].map(v => (
          <div key={v} className="w-3 h-3 rounded-sm"
            style={{ backgroundColor: v === 0 ? '#1e1e2e' : `#00ff9d${Math.round(v * 100 + 20).toString(16).padStart(2, '0')}` }} />
        ))}
        <span className="text-[10px] font-mono text-forge-text-3">More</span>
      </div>
    </div>
  )
}

const PRIORITY_COLORS = {
  low: '#55556a', medium: '#4d9fff', high: '#ff7b3a', urgent: '#ff3a5c'
}

export function Analytics() {
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [trendDays, setTrendDays] = useState(30)

  async function load() {
    try {
      const d = await analyticsApi.dashboard()
      setData(d)
    } catch {
      toast.error('Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleRefresh() {
    setRefreshing(true)
    try {
      await analyticsApi.invalidate()
      await load()
      toast.success('Analytics refreshed')
    } catch {
      toast.error('Refresh failed')
    } finally {
      setRefreshing(false)
    }
  }

  async function handleExport() {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`/api/v1/analytics/export/csv?days=${trendDays}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href = url; a.download = `taskforge_${trendDays}d.csv`; a.click()
      URL.revokeObjectURL(url)
      toast.success('CSV downloaded')
    } catch {
      toast.error('Export failed')
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen"><Spinner size="lg" /></div>
  )

  const trendData = (data?.daily_trend || [])
    .slice(-trendDays)
    .map(d => ({
      date: format(parseISO(d.date), 'MMM d'),
      Completed: d.completed,
      Created: d.created,
    }))

  const priorityData = (data?.by_priority || []).map(p => ({
    name: p.priority,
    value: p.count,
    color: PRIORITY_COLORS[p.priority] || '#55556a'
  })).filter(p => p.value > 0)

  const statusData = Object.entries(data?.by_status || {}).map(([k, v]) => ({
    name: k.replace('_', ' '),
    count: v
  }))

  const score = data?.productivity?.score ?? 0
  const scoreColor = score >= 70 ? '#00ff9d' : score >= 40 ? '#ff7b3a' : '#ff3a5c'

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6 animate-fade-in">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-2xl text-forge-text">Analytics</h1>
          <p className="text-forge-text-3 text-sm mt-0.5">
            {data?.generated_at && `Last updated ${format(parseISO(data.generated_at), 'MMM d, HH:mm')}`}
            {data?.cached && <span className="ml-2 badge bg-forge-muted/50 text-forge-text-3">cached</span>}
          </p>
        </div>
        <div className="flex gap-3">
          <button onClick={handleExport} className="btn-ghost flex items-center gap-2 text-sm">
            <Download size={14} /> Export CSV
          </button>
          <button onClick={handleRefresh} disabled={refreshing}
            className="btn-ghost flex items-center gap-2 text-sm">
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Top KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Productivity Score', value: `${score}`, unit: '/ 100', color: scoreColor, icon: Award },
          { label: 'Completion Rate',    value: `${data?.rates?.completion_pct ?? 0}`, unit: '%', color: '#00ff9d', icon: TrendingUp },
          { label: 'On-time Rate',       value: `${data?.rates?.on_time_pct ?? 0}`,    unit: '%', color: '#4d9fff', icon: TrendingUp },
          { label: 'Current Streak',     value: `${data?.productivity?.streak_days ?? 0}`, unit: 'days', color: '#ff7b3a', icon: Flame },
        ].map(({ label, value, unit, color, icon: Icon }) => (
          <div key={label} className="stat-card">
            <div className="flex items-center justify-between">
              <Icon size={16} style={{ color }} />
              <span className="font-mono text-[10px]" style={{ color }}>{unit}</span>
            </div>
            <div className="mt-3">
              <p className="font-display font-bold text-3xl" style={{ color }}>{value}</p>
              <p className="text-xs font-mono text-forge-text-3 mt-0.5 uppercase tracking-wider">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Trend chart */}
      <div className="card">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-display font-semibold text-forge-text">Task Activity Trend</h2>
          <div className="flex gap-1.5">
            {[7, 14, 30, 90].map(d => (
              <button key={d} onClick={() => setTrendDays(d)}
                className={`px-2.5 py-1 text-xs font-mono rounded-md transition-colors
                  ${trendDays === d
                    ? 'bg-forge-accent/15 text-forge-accent'
                    : 'text-forge-text-3 hover:text-forge-text hover:bg-forge-muted'}`}>
                {d}d
              </button>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={trendData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="gc" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00ff9d" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#00ff9d" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gcr" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4d9fff" stopOpacity={0.1} />
                <stop offset="95%" stopColor="#4d9fff" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#55556a', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fontSize: 10, fill: '#55556a', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="Completed" stroke="#00ff9d" strokeWidth={2} fill="url(#gc)" dot={false} />
            <Area type="monotone" dataKey="Created" stroke="#4d9fff" strokeWidth={2} fill="url(#gcr)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Status breakdown bar */}
        <div className="card">
          <h2 className="font-display font-semibold text-forge-text mb-5">Tasks by Status</h2>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={statusData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#55556a', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#55556a', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" fill="#00ff9d" opacity={0.8} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Priority pie */}
        <div className="card">
          <h2 className="font-display font-semibold text-forge-text mb-5">Tasks by Priority</h2>
          {priorityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={priorityData} cx="50%" cy="50%" innerRadius={50} outerRadius={75}
                  paddingAngle={3} dataKey="value">
                  {priorityData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} opacity={0.85} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  formatter={(v) => <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono', color: '#9090a8' }}>{v}</span>}
                  iconType="circle" iconSize={8}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[180px] flex items-center justify-center text-forge-text-3 text-sm">
              No task data yet
            </div>
          )}
        </div>
      </div>

      {/* Heatmap */}
      <div className="card">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-display font-semibold text-forge-text">Activity Heatmap</h2>
          <span className="text-xs font-mono text-forge-text-3">Last 12 weeks</span>
        </div>
        <Heatmap data={data?.heatmap} />
      </div>
    </div>
  )
}
