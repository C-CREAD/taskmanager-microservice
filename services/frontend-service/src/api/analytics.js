import { api } from './client'

export const analyticsApi = {
  dashboard:    ()           => api.get('/analytics/dashboard'),
  summary:      ()           => api.get('/analytics/summary'),
  trend:        (days = 30)  => api.get(`/analytics/trend?days=${days}`),
  heatmap:      (weeks = 12) => api.get(`/analytics/heatmap?weeks=${weeks}`),
  score:        ()           => api.get('/analytics/score'),
  invalidate:   ()           => api.post('/analytics/cache/invalidate', {}),
}
