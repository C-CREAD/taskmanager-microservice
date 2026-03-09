import { api } from './client'

export const tasksApi = {
  list:       (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return api.get(`/tasks/${q ? '?' + q : ''}`)
  },
  get:        (id)          => api.get(`/tasks/${id}/`),
  create:     (data)        => api.post('/tasks/', data),
  update:     (id, data)    => api.patch(`/tasks/${id}/`, data),
  delete:     (id)          => api.delete(`/tasks/${id}/`),
  updateStatus: (id, status) => api.patch(`/tasks/${id}/status/`, { status }),
  complete:   (id)          => api.post(`/tasks/${id}/complete/`),
  stats:      ()            => api.get('/tasks/stats/'),

  listCategories: ()        => api.get('/categories/'),
  createCategory: (data)    => api.post('/categories/', data),
}
