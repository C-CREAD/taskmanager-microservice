import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { tasksApi } from '../api/tasks'
import { Spinner } from '../components/ui/Spinner'
import { Empty } from '../components/ui/Empty'
import { Modal } from '../components/ui/Modal'
import {
  Plus, Search, Filter, CheckSquare, Calendar,
  Trash2, Check, MoreHorizontal, ChevronLeft, ChevronRight,
  Tag, User, Flag
} from 'lucide-react'
import { format, parseISO, isPast } from 'date-fns'
import toast from 'react-hot-toast'

const STATUSES  = ['todo', 'in_progress', 'in_review', 'done', 'cancelled']
const PRIORITIES = ['low', 'medium', 'high', 'urgent']

const STATUS_TRANSITIONS = {
  todo:        ['in_progress', 'cancelled'],
  in_progress: ['in_review', 'todo', 'cancelled'],
  in_review:   ['done', 'in_progress'],
  done:        [],
  cancelled:   [],
}

function TaskRow({ task, onUpdate, onDelete }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [transitioning, setTransitioning] = useState(false)
  const overdue = task.due_date && isPast(parseISO(task.due_date)) && task.status !== 'done' && task.status !== 'cancelled'

  async function handleStatusChange(status) {
    setTransitioning(true)
    try {
      const updated = await tasksApi.updateStatus(task.id, status)
      onUpdate(updated)
      toast.success(`Moved to ${status.replace('_', ' ')}`)
    } catch (e) {
      toast.error(e?.detail || 'Failed to update status')
    } finally {
      setTransitioning(false)
      setMenuOpen(false)
    }
  }

  async function handleComplete() {
    setTransitioning(true)
    try {
      const updated = await tasksApi.complete(task.id)
      onUpdate(updated)
      toast.success('Task completed! 🎉')
    } catch (e) {
      toast.error(e?.detail || 'Failed')
    } finally {
      setTransitioning(false)
    }
  }

  async function handleDelete() {
    try {
      await tasksApi.delete(task.id)
      onDelete(task.id)
      toast.success('Task deleted')
    } catch {
      toast.error('Failed to delete')
    }
    setMenuOpen(false)
  }

  const nextStatuses = STATUS_TRANSITIONS[task.status] || []

  return (
    <div className={`group flex items-start gap-4 px-5 py-4 border-b border-forge-border
      hover:bg-forge-muted/20 transition-colors duration-150
      ${task.status === 'done' ? 'opacity-60' : ''}`}>

      {/* Complete button */}
      <button
        onClick={handleComplete}
        disabled={task.status === 'done' || task.status === 'cancelled' || transitioning}
        className={`mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0
          transition-all duration-200
          ${task.status === 'done'
            ? 'border-forge-accent bg-forge-accent'
            : 'border-forge-muted group-hover:border-forge-accent/60 hover:border-forge-accent'}`}
      >
        {task.status === 'done' && <Check size={11} className="text-forge-bg" strokeWidth={3} />}
      </button>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start gap-3 flex-wrap">
          <p className={`text-sm font-body font-medium text-forge-text flex-1 min-w-0
            ${task.status === 'done' ? 'line-through text-forge-text-3' : ''}`}>
            {task.title}
          </p>
          <div className="flex items-center gap-2 shrink-0">
            <span className={`badge-${task.status}`}>{task.status.replace('_', ' ')}</span>
            <span className={`badge-${task.priority}`}>{task.priority}</span>
          </div>
        </div>

        {task.description && (
          <p className="text-xs text-forge-text-3 mt-1 line-clamp-1">{task.description}</p>
        )}

        <div className="flex items-center gap-4 mt-2">
          {task.due_date && (
            <span className={`flex items-center gap-1 text-xs font-mono
              ${overdue ? 'text-forge-danger' : 'text-forge-text-3'}`}>
              <Calendar size={11} />
              {format(parseISO(task.due_date), 'MMM d')}
              {overdue && ' · overdue'}
            </span>
          )}
          {task.category && (
            <span className="flex items-center gap-1 text-xs text-forge-text-3">
              <Tag size={11} />
              {task.category_name || task.category}
            </span>
          )}
          {task.tags?.length > 0 && (
            <div className="flex gap-1">
              {task.tags.slice(0, 3).map(t => (
                <span key={t} className="badge bg-forge-muted/50 text-forge-text-3">{t}</span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="relative shrink-0">
        <button
          onClick={() => setMenuOpen(p => !p)}
          className="p-1.5 rounded-lg text-forge-text-3 hover:text-forge-text
            hover:bg-forge-muted opacity-0 group-hover:opacity-100 transition-all">
          <MoreHorizontal size={15} />
        </button>

        {menuOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
            <div className="absolute right-0 top-8 z-20 w-44 bg-forge-surface border border-forge-border
              rounded-xl shadow-2xl overflow-hidden animate-slide-up">
              {nextStatuses.length > 0 && (
                <>
                  <p className="px-3 pt-2.5 pb-1 text-[10px] font-mono text-forge-text-3 uppercase tracking-wider">
                    Move to
                  </p>
                  {nextStatuses.map(s => (
                    <button key={s} onClick={() => handleStatusChange(s)}
                      className="w-full px-3 py-2 text-left text-sm text-forge-text-2
                        hover:bg-forge-muted hover:text-forge-text transition-colors flex items-center gap-2">
                      <span className={`badge-${s} py-0`}>{s.replace('_', ' ')}</span>
                    </button>
                  ))}
                  <div className="border-t border-forge-border my-1" />
                </>
              )}
              <button onClick={handleDelete}
                className="w-full px-3 py-2 text-left text-sm text-forge-danger
                  hover:bg-forge-danger/10 transition-colors flex items-center gap-2">
                <Trash2 size={13} />
                Delete
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function TaskForm({ onSave, onClose, categories }) {
  const [form, setForm] = useState({
    title: '', description: '', priority: 'medium', status: 'todo',
    due_date: '', category: '', tags: ''
  })
  const [loading, setLoading] = useState(false)
  const set = k => e => setForm(p => ({ ...p, [k]: e.target.value }))

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      const payload = {
        title:       form.title,
        description: form.description || null,
        priority:    form.priority,
        status:      form.status,
        due_date:    form.due_date || null,
        category:    form.category ? parseInt(form.category) : null,
        tags:        form.tags ? form.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
      }
      const task = await tasksApi.create(payload)
      onSave(task)
      toast.success('Task created!')
    } catch (e) {
      toast.error(e?.detail || 'Failed to create task')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-xs font-mono text-forge-text-3 mb-1.5 uppercase tracking-wider">Title *</label>
        <input className="input" placeholder="What needs to be done?" value={form.title} onChange={set('title')} required />
      </div>
      <div>
        <label className="block text-xs font-mono text-forge-text-3 mb-1.5 uppercase tracking-wider">Description</label>
        <textarea className="input resize-none h-20" placeholder="Optional details..." value={form.description} onChange={set('description')} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-mono text-forge-text-3 mb-1.5 uppercase tracking-wider">Priority</label>
          <select className="input" value={form.priority} onChange={set('priority')}>
            {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-mono text-forge-text-3 mb-1.5 uppercase tracking-wider">Due Date</label>
          <input className="input" type="datetime-local" value={form.due_date} onChange={set('due_date')} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-mono text-forge-text-3 mb-1.5 uppercase tracking-wider">Category</label>
          <select className="input" value={form.category} onChange={set('category')}>
            <option value="">None</option>
            {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-mono text-forge-text-3 mb-1.5 uppercase tracking-wider">Tags</label>
          <input className="input" placeholder="work, urgent, bug" value={form.tags} onChange={set('tags')} />
        </div>
      </div>
      <div className="flex gap-3 pt-1">
        <button type="submit" disabled={loading} className="btn-primary flex-1">
          {loading ? <Spinner size="sm" className="mx-auto" /> : 'Create Task'}
        </button>
        <button type="button" onClick={onClose} className="btn-ghost">Cancel</button>
      </div>
    </form>
  )
}

export function Tasks() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [tasks, setTasks]         = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading]     = useState(true)
  const [total, setTotal]         = useState(0)
  const [showCreate, setShowCreate] = useState(false)

  const [filters, setFilters] = useState({
    search:   searchParams.get('search')   || '',
    status:   searchParams.get('status')   || '',
    priority: searchParams.get('priority') || '',
    page:     parseInt(searchParams.get('page') || '1'),
  })

  const fetchTasks = useCallback(async () => {
    setLoading(true)
    try {
      const params = {
        page:      filters.page,
        page_size: 20,
        ...(filters.search   && { search:   filters.search }),
        ...(filters.status   && { status:   filters.status }),
        ...(filters.priority && { priority: filters.priority }),
      }
      const data = await tasksApi.list(params)
      setTasks(data.results || [])
      setTotal(data.count || 0)
    } catch {
      toast.error('Failed to load tasks')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { fetchTasks() }, [fetchTasks])

  useEffect(() => {
    tasksApi.listCategories().then(d => setCategories(d.results || d)).catch(() => {})
  }, [])

  function setFilter(key, value) {
    setFilters(p => ({ ...p, [key]: value, page: 1 }))
    setSearchParams(prev => {
      if (value) prev.set(key, value); else prev.delete(key)
      prev.delete('page')
      return prev
    })
  }

  function handleUpdate(updated) {
    setTasks(tasks => tasks.map(t => t.id === updated.id ? updated : t))
  }

  function handleDelete(id) {
    setTasks(tasks => tasks.filter(t => t.id !== id))
    setTotal(c => c - 1)
  }

  function handleCreated(task) {
    setTasks(p => [task, ...p])
    setTotal(c => c + 1)
    setShowCreate(false)
  }

  const totalPages = Math.ceil(total / 20)

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-5 animate-fade-in">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-2xl text-forge-text">Tasks</h1>
          <p className="text-forge-text-3 text-sm mt-0.5">
            {total > 0 ? `${total} task${total !== 1 ? 's' : ''}` : 'No tasks yet'}
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus size={15} />
          New Task
        </button>
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[200px] relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-forge-text-3" />
          <input className="input pl-8" placeholder="Search tasks..."
            value={filters.search}
            onChange={e => setFilter('search', e.target.value)} />
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Filter size={14} className="text-forge-text-3" />
          <select className="input w-auto text-sm py-2" value={filters.status} onChange={e => setFilter('status', e.target.value)}>
            <option value="">All statuses</option>
            {STATUSES.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
          </select>
          <select className="input w-auto text-sm py-2" value={filters.priority} onChange={e => setFilter('priority', e.target.value)}>
            <option value="">All priorities</option>
            {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          {(filters.status || filters.priority || filters.search) && (
            <button onClick={() => {
              setFilters({ search: '', status: '', priority: '', page: 1 })
              setSearchParams({})
            }} className="text-xs text-forge-danger hover:text-forge-danger/80 transition-colors font-mono">
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Task list */}
      <div className="card p-0 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16"><Spinner /></div>
        ) : tasks.length === 0 ? (
          <Empty icon={CheckSquare} title="No tasks found"
            description={filters.search || filters.status || filters.priority
              ? 'Try adjusting your filters' : 'Create your first task to get started'}
            action={<button onClick={() => setShowCreate(true)} className="btn-primary">Create a task</button>}
          />
        ) : (
          tasks.map(task => (
            <TaskRow key={task.id} task={task} onUpdate={handleUpdate} onDelete={handleDelete} />
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs font-mono text-forge-text-3">
            Page {filters.page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button disabled={filters.page <= 1} onClick={() => setFilter('page', filters.page - 1)}
              className="btn-ghost px-2.5 py-1.5 disabled:opacity-40">
              <ChevronLeft size={15} />
            </button>
            <button disabled={filters.page >= totalPages} onClick={() => setFilter('page', filters.page + 1)}
              className="btn-ghost px-2.5 py-1.5 disabled:opacity-40">
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      )}

      {/* Create modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="New Task" size="md">
        <TaskForm onSave={handleCreated} onClose={() => setShowCreate(false)} categories={categories} />
      </Modal>
    </div>
  )
}
