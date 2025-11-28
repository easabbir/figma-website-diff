import { useState } from 'react'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import ComparisonForm from './components/ComparisonForm'
import ReportDisplay from './components/ReportDisplay'
import Header from './components/Header'

export interface ComparisonResult {
  jobId: string
  status: string
}

function App() {
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null)
  const [showReport, setShowReport] = useState(false)

  const handleComparisonStart = (result: ComparisonResult) => {
    setComparisonResult(result)
    setShowReport(true)
  }

  const handleBack = () => {
    setShowReport(false)
    setComparisonResult(null)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <Header />
      
      <main className="container mx-auto px-4 py-8 max-w-7xl">
        {!showReport ? (
          <ComparisonForm onComparisonStart={handleComparisonStart} />
        ) : (
          <ReportDisplay jobId={comparisonResult?.jobId || ''} onBack={handleBack} />
        )}
      </main>

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
