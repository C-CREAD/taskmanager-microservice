import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import { AppLayout } from './components/layout/AppLayout'
import { PageSpinner } from './components/ui/Spinner'
import { Login }         from './pages/Login'
import { Register }      from './pages/Register'
import { Dashboard }     from './pages/Dashboard'
import { Tasks }         from './pages/Tasks'
import { Notifications } from './pages/Notifications'
import { Analytics }     from './pages/Analytics'
import { Profile }       from './pages/Profile'
import './styles/globals.css'

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <PageSpinner />
  return user ? children : <Navigate to="/login" replace />
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <PageSpinner />
  return user ? <Navigate to="/" replace /> : children
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public */}
          <Route path="/login"    element={<PublicRoute><Login /></PublicRoute>} />
          <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />

          {/* Protected */}
          <Route element={<PrivateRoute><AppLayout /></PrivateRoute>}>
            <Route path="/"              element={<Dashboard />} />
            <Route path="/tasks"         element={<Tasks />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/analytics"     element={<Analytics />} />
            <Route path="/profile"       element={<Profile />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>

        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#111118',
              color: '#e8e8f0',
              border: '1px solid #1e1e2e',
              fontFamily: 'DM Sans, sans-serif',
              fontSize: '13px',
              borderRadius: '12px',
            },
            success: { iconTheme: { primary: '#00ff9d', secondary: '#0a0a0f' } },
            error:   { iconTheme: { primary: '#ff3a5c', secondary: '#0a0a0f' } },
          }}
        />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)
