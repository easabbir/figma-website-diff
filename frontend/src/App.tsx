import { useState, useEffect, useRef } from 'react'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import { AuthProvider, useAuth } from './context/AuthContext'
import ComparisonForm from './components/ComparisonForm'
import ReportDisplay from './components/ReportDisplay'
import Header from './components/Header'
import HistoryView from './components/HistoryView'
import AuthPage from './components/AuthPage'
import ForgotPasswordPage from './components/ForgotPasswordPage'
import ResetPasswordPage from './components/ResetPasswordPage'

type AuthView = 'login' | 'forgot-password' | 'reset-password'

export interface ComparisonResult {
  jobId: string
  status: string
}

export interface CachedFormData {
  figmaUrl: string
  figmaToken: string
  figmaNodeId?: string
  websiteUrl: string
  viewportWidth: string
  viewportHeight: string
  comparisonMode: string
}

function MainApp() {
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null)
  const [showReport, setShowReport] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [cachedFormData, setCachedFormData] = useState<CachedFormData | null>(null)
  const [isFromHistory, setIsFromHistory] = useState(false)
  const [authView, setAuthView] = useState<AuthView>('login')
  const [resetEmail, setResetEmail] = useState('')
  const [resetToken, setResetToken] = useState('')
  const { isAuthenticated, isLoading, user } = useAuth()
  const prevUserIdRef = useRef<string | null>(null)

  // Check for password reset URL params on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const email = params.get('email')
    const token = params.get('token')
    
    if (email && token && window.location.pathname === '/reset-password') {
      setResetEmail(email)
      setResetToken(token)
      setAuthView('reset-password')
      // Clean up URL
      window.history.replaceState({}, '', '/')
    }
  }, [])

  // Clear form data when user changes (login/logout)
  useEffect(() => {
    const currentUserId = user?.id || null
    if (prevUserIdRef.current !== null && prevUserIdRef.current !== currentUserId) {
      // User changed - clear form and report
      setCachedFormData(null)
      setComparisonResult(null)
      setShowReport(false)
      setIsFromHistory(false)
    }
    prevUserIdRef.current = currentUserId
  }, [user])

  const handleComparisonStart = (result: ComparisonResult, formData: CachedFormData) => {
    setCachedFormData(formData)
    setComparisonResult(result)
    setIsFromHistory(false)
    setShowReport(true)
  }

  const handleBack = () => {
    setShowReport(false)
    setIsFromHistory(false)
  }

  const handleSelectFromHistory = (jobId: string) => {
    setComparisonResult({ jobId, status: 'completed' })
    setIsFromHistory(true)
    setShowReport(true)
    setShowHistory(false)
  }

  // Show loading spinner while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      </div>
    )
  }

  // Show auth page if not authenticated
  if (!isAuthenticated) {
    if (authView === 'forgot-password') {
      return (
        <ForgotPasswordPage 
          onBack={() => setAuthView('login')} 
        />
      )
    }
    
    if (authView === 'reset-password') {
      return (
        <ResetPasswordPage 
          email={resetEmail}
          token={resetToken}
          onBack={() => setAuthView('login')}
          onSuccess={() => setAuthView('login')}
        />
      )
    }
    
    return (
      <AuthPage 
        onForgotPassword={() => setAuthView('forgot-password')} 
      />
    )
  }

  // Show main app if authenticated
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <Header />
      
      <main className="container mx-auto px-4 py-8 max-w-7xl">
        {!showReport ? (
          <ComparisonForm 
            onComparisonStart={handleComparisonStart} 
            cachedData={cachedFormData}
            onShowHistory={() => setShowHistory(true)}
          />
        ) : (
          <ReportDisplay jobId={comparisonResult?.jobId || ''} onBack={handleBack} fromHistory={isFromHistory} />
        )}
      </main>

      {/* History Modal */}
      {showHistory && (
        <HistoryView
          onSelectJob={handleSelectFromHistory}
          onClose={() => setShowHistory(false)}
        />
      )}
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <MainApp />
      <ToastContainer
        position="top-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
      />
    </AuthProvider>
  )
}

export default App
