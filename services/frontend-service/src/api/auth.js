import { api } from './client'

export const authApi = {
  register: (data)  => api.post('/auth/register', data),
  login:    (data)  => api.post('/auth/login', data),
  logout:   ()      => api.post('/auth/logout', {}),
  me:       ()      => api.get('/users/me'),
  update:   (data)  => api.patch('/users/me', data),
  changePassword: (data) => api.post('/users/me/change-password', data),
}
