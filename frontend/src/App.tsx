import { Routes, Route, Navigate } from 'react-router'
import { Suspense, lazy } from 'react'
import { Toaster } from 'sonner'
import { BackgroundProvider } from './hooks/useBackground'
import { useAuth } from './lib/authContext'
import { AuthModal } from './components/Auth/AuthModal'
import CommandPalette from './components/CommandPalette'
import TodoDemo from './components/TodoDemo'

const ResearchModule = lazy(() => import('./modules/research/ResearchModule'))
const NotesModule = lazy(() => import('./modules/notes/NotesModule'))
const DocumentsModule = lazy(() => import('./modules/documents/DocumentsModule'))

const LoadingFallback = () => (
  <div className="h-screen w-full flex items-center justify-center bg-black text-[#999]">
    <div className="w-8 h-8 border-2 border-[#333] border-t-[#c8956c] rounded-full animate-spin" />
  </div>
)

export default function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-black text-[#999]">
        Loading session…
      </div>
    )
  }

  if (!user) {
    return (
      <div className="h-screen w-full bg-black relative">
        <AuthModal />
        <Toaster 
          position="bottom-right" 
          theme="dark" 
          toastOptions={{
            style: {
              background: 'rgba(0,0,0,0.9)',
              border: '1px solid rgba(255,255,255,0.06)',
              color: '#e0e0e0',
              backdropFilter: 'blur(6px) saturate(140%)',
            },
          }}
        />
      </div>
    )
  }

  return (
    <BackgroundProvider>
      <CommandPalette />
      <Suspense fallback={<LoadingFallback />}>
        <Routes>
          <Route path="/research/*" element={<ResearchModule />} />
          <Route path="/notes/*" element={<NotesModule />} />
          <Route path="/documents/*" element={<DocumentsModule />} />
          <Route path="/todo" element={<TodoDemo />} />
          <Route path="/" element={<Navigate to="/research" replace />} />
        </Routes>
      </Suspense>
      <Toaster 
        position="bottom-right" 
        theme="dark" 
        toastOptions={{
          style: {
            background: 'rgba(0,0,0,0.9)',
            border: '1px solid rgba(255,255,255,0.06)',
            color: '#e0e0e0',
            backdropFilter: 'blur(6px) saturate(140%)',
          },
        }}
      />
    </BackgroundProvider>
  )
}
