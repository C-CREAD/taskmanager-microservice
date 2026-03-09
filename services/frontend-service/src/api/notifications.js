import { api } from './client'

export const notifApi = {
  list:       (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return api.get(`/notifications/${q ? '?' + q : ''}`)
  },
  unreadCount:  ()   => api.get('/notifications/unread-count'),
  markRead:     (id) => api.patch(`/notifications/${id}/read`),
  markAllRead:  ()   => api.post('/notifications/read-all', {}),
  getPrefs:     ()   => api.get('/preferences/'),
  updatePrefs:  (d)  => api.patch('/preferences/', d),
}

export function createWebSocket(token, onMessage) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(`${protocol}//${window.location.host}/api/v1/ws`)

  ws.onopen = () => {
    ws.send(JSON.stringify({ token }))
  }

  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.event === 'notification') onMessage(data)
    } catch {}
  }

  ws.onerror = () => {}

  return ws
}
