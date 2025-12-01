import { useState } from 'react'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import ComparisonForm from './components/ComparisonForm'
import ReportDisplay from './components/ReportDisplay'
import Header from './components/Header'
import HistoryView from './components/HistoryView'

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

function App() {
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null)
  const [showReport, setShowReport] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [cachedFormData, setCachedFormData] = useState<CachedFormData | null>(null)
  const [isFromHistory, setIsFromHistory] = useState(false)

  const handleComparisonStart = (result: ComparisonResult, formData: CachedFormData) => {
    setCachedFormData(formData)
    setComparisonResult(result)
    setIsFromHistory(false)
    setShowReport(true)
  }

  const handleBack = () => {
    setShowReport(false)
    setIsFromHistory(false)
    // Keep cachedFormData so form can restore it
  }

  const handleSelectFromHistory = (jobId: string) => {
    setComparisonResult({ jobId, status: 'completed' })
    setIsFromHistory(true)
    setShowReport(true)
    setShowHistory(false)
  }

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
    </div>
  )
}

export default App
