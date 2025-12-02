import { useState, useEffect } from 'react'
import { ArrowLeft, Download, CheckCircle, AlertCircle, Info, Loader2, FileText, ImageOff } from 'lucide-react'
import axios from 'axios'
import { toast } from 'react-toastify'
import {
  ReactCompareSlider,
  ReactCompareSliderImage
} from 'react-compare-slider'
import DiffViewer from './DiffViewer'

interface ReportDisplayProps {
  jobId: string
  onBack: () => void
  fromHistory?: boolean  // If true, skip progress polling and fetch report directly
}

interface DiffReport {
  job_id: string
  status: string
  summary: {
    total_differences: number
    critical: number
    warnings: number
    info: number
    match_score: number
  }
  differences: any[]
  figma_screenshot_url?: string
  website_screenshot_url?: string
  visual_diff_url?: string
  report_html_url?: string
  error?: string
}

export default function ReportDisplay({ jobId, onBack, fromHistory = false }: ReportDisplayProps) {
  const [report, setReport] = useState<DiffReport | null>(null)
  const [progress, setProgress] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'slider' | 'sideBySide'>('slider')
  const [figmaImageError, setFigmaImageError] = useState(false)
  const [websiteImageError, setWebsiteImageError] = useState(false)
  const [toastShown, setToastShown] = useState(false)

  useEffect(() => {
    let progressInterval: ReturnType<typeof setInterval>
    let reportFetched = false  // Prevent multiple fetches/toasts

    const fetchProgress = async () => {
      try {
        const response = await axios.get(`/api/v1/progress/${jobId}`)
        setProgress(response.data.progress)
        console.log('Progress update:', response.data.status, response.data.progress + '%', response.data.message)

        if ((response.data.status === 'completed' || response.data.status === 'failed') && !reportFetched) {
          reportFetched = true
          clearInterval(progressInterval)
          fetchReport(false)
        }
      } catch (err: any) {
        console.error('Error fetching progress:', err)
        clearInterval(progressInterval)
        // If from history and progress not found, try to fetch report directly
        if (fromHistory) {
          console.log('Progress not found for historical job, fetching report directly')
          fetchReport(true)
        } else {
          setError(`Failed to fetch progress: ${err.message}`)
          setLoading(false)
        }
      }
    }

    const fetchReport = async (isHistorical: boolean) => {
      try {
        const response = await axios.get(`/api/v1/report/${jobId}`)
        
        // Only process if we got a complete report (status 200)
        console.log('Report response:', response.data)
        console.log('Summary:', response.data.summary)
        
        setReport(response.data)
        setLoading(false)

        if (response.data.status === 'failed') {
          const errorMsg = response.data.error || 'Comparison failed'
          setError(errorMsg)
          
          // Show toast only once - error is already displayed on the page
          // No toast needed here as the error page provides full details
        } else if (!isHistorical && !toastShown) {
          // Only show toast for new comparisons, not historical ones, and only once
          setToastShown(true)
          toast.success('✅ Comparison completed successfully!')
        }
      } catch (err: any) {
        if (err.response?.status === 202) {
          // Still processing - this shouldn't happen since we only call after progress shows complete
          console.log('Unexpected 202 response when fetching report')
          reportFetched = false  // Allow retry
          return
        }
        console.error('Error fetching report:', err)
        setError('Failed to load report')
        setLoading(false)
      }
    }

    // If from history, try to fetch report directly first
    if (fromHistory) {
      setProgress(100)
      fetchReport(true)
    } else {
      // Poll for progress only - report will be fetched when progress shows completion
      progressInterval = setInterval(fetchProgress, 1000)
      // Initial fetch
      fetchProgress()
    }

    return () => {
      clearInterval(progressInterval)
    }
  }, [jobId])

  const downloadReport = () => {
    if (report?.report_html_url) {
      window.open(report.report_html_url, '_blank')
    }
  }

  const downloadPDF = async () => {
    try {
      toast.info('Generating PDF report...')
      const response = await axios.get(`/api/v1/report/${jobId}/pdf`, {
        responseType: 'blob'
      })
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `ui-comparison-${jobId.slice(0, 8)}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      
      toast.success('PDF downloaded successfully!')
    } catch (err) {
      toast.error('Failed to download PDF report')
      console.error('PDF download error:', err)
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card text-center py-12">
          <Loader2 className="w-16 h-16 text-primary-600 animate-spin mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Processing Comparison...
          </h2>
          <p className="text-gray-600 mb-6">
            This may take a minute. Please wait while we analyze your design and website.
          </p>

          {/* Progress Bar */}
          <div className="max-w-md mx-auto">
            <div className="w-full bg-gray-200 rounded-full h-3 mb-2 overflow-hidden">
              <div
                className="bg-primary-600 h-full transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-sm text-gray-600">{progress}% Complete</p>
          </div>
        </div>
      </div>
    )
  }

  if (error || !report) {
    // Parse error for user-friendly display
    const errorMessage = error || 'Failed to load report'
    const isRateLimit = errorMessage.includes('429') || errorMessage.toLowerCase().includes('too many requests')
    const isForbidden = errorMessage.includes('403') || errorMessage.toLowerCase().includes('forbidden')
    const isAuthError = errorMessage.includes('401') || errorMessage.toLowerCase().includes('unauthorized')
    const isNotFound = errorMessage.includes('404') || errorMessage.toLowerCase().includes('not found')
    const isTimeout = errorMessage.toLowerCase().includes('timeout')
    
    let errorTitle = 'Comparison Failed'
    let errorDescription = errorMessage
    let suggestion = ''
    let icon = '❌'
    
    if (isRateLimit) {
      errorTitle = 'Rate Limit Exceeded'
      errorDescription = 'Figma API has temporarily blocked requests due to too many calls.'
      suggestion = "Oops! You've hit the rate limit. Give it a moment and try again soon. For higher limits, consider using OAuth."
      icon = '⏳'
    } else if (isForbidden) {
      errorTitle = 'Access Denied'
      errorDescription = "You don't have permission to access this Figma file."
      suggestion = "Make sure the file is shared with you or is publicly accessible. If using OAuth, try disconnecting and reconnecting to refresh permissions."
      icon = '🚫'
    } else if (isAuthError) {
      errorTitle = 'Authentication Failed'
      errorDescription = 'Your Figma token is invalid or has expired.'
      suggestion = 'Please reconnect with OAuth or generate a new personal access token.'
      icon = '🔑'
    } else if (isNotFound) {
      errorTitle = 'Design Not Found'
      errorDescription = 'The Figma file or frame could not be found.'
      suggestion = 'Please check your Figma URL and ensure the node ID is correct.'
      icon = '🔍'
    } else if (isTimeout) {
      errorTitle = 'Request Timed Out'
      errorDescription = 'The request took too long to complete.'
      suggestion = 'Try with a smaller frame or check if the website is accessible.'
      icon = '⏱️'
    }
    
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card text-center py-12">
          <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <span className="text-4xl">{icon}</span>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">{errorTitle}</h2>
          <p className="text-gray-600 mb-3 max-w-lg mx-auto">{errorDescription}</p>
          {suggestion && (
            <p className="text-sm text-primary-600 mb-6 max-w-lg mx-auto bg-primary-50 px-4 py-2 rounded-lg inline-block">
              💡 {suggestion}
            </p>
          )}
          <div className="mt-4">
            <button onClick={onBack} className="btn-primary">
              ← Try Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Add safety check for summary
  if (!report.summary || typeof report.summary !== 'object') {
    console.error('Report missing or invalid summary:', {
      report,
      hasSummary: !!report.summary,
      summaryType: typeof report.summary,
      summaryKeys: report.summary ? Object.keys(report.summary) : 'N/A'
    })
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card text-center py-12">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Invalid Report Data</h2>
          <p className="text-gray-600 mb-6">
            The report data is incomplete or invalid. Check browser console for details.
          </p>
          <pre className="text-xs text-left bg-gray-100 p-4 rounded mt-4 overflow-auto max-h-40">
            {JSON.stringify(report, null, 2)}
          </pre>
          <button onClick={onBack} className="btn-primary mt-4">
            Go Back
          </button>
        </div>
      </div>
    )
  }

  const { summary } = report

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-gray-700 hover:text-primary-600 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          New Comparison
        </button>

        <div className="flex gap-2">
          <button onClick={downloadPDF} className="btn-primary flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Download PDF
          </button>
          <button onClick={downloadReport} className="btn-secondary flex items-center gap-2">
            <Download className="w-4 h-4" />
            HTML Report
          </button>
        </div>
      </div>

      {/* Match Score Card */}
      <div className="card mb-6 text-center">
        <h2 className="text-lg font-semibold text-gray-700 mb-4">Overall Match Score</h2>
        <div className="relative inline-flex items-center justify-center">
          <svg className="w-40 h-40 transform -rotate-90">
            <circle
              cx="80"
              cy="80"
              r="70"
              stroke="#e5e7eb"
              strokeWidth="12"
              fill="none"
            />
            <circle
              cx="80"
              cy="80"
              r="70"
              stroke={summary.match_score >= 80 ? '#10b981' : summary.match_score >= 60 ? '#f59e0b' : '#ef4444'}
              strokeWidth="12"
              fill="none"
              strokeDasharray={`${2 * Math.PI * 70}`}
              strokeDashoffset={`${2 * Math.PI * 70 * (1 - summary.match_score / 100)}`}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute">
            <p className="text-4xl font-bold text-gray-900">
              {summary.match_score.toFixed(1)}%
            </p>
          </div>
        </div>
        <p className="text-sm text-gray-600 mt-4">
          Based on visual similarity and structural comparison
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Total Differences</p>
              <p className="text-3xl font-bold text-gray-900">{summary.total_differences}</p>
            </div>
            <Info className="w-8 h-8 text-gray-400" />
          </div>
        </div>

        <div className="card border-l-4 border-red-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Critical</p>
              <p className="text-3xl font-bold text-red-600">{summary.critical}</p>
            </div>
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
        </div>

        <div className="card border-l-4 border-yellow-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Warnings</p>
              <p className="text-3xl font-bold text-yellow-600">{summary.warnings}</p>
            </div>
            <AlertCircle className="w-8 h-8 text-yellow-500" />
          </div>
        </div>

        <div className="card border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Info</p>
              <p className="text-3xl font-bold text-blue-600">{summary.info}</p>
            </div>
            <CheckCircle className="w-8 h-8 text-blue-500" />
          </div>
        </div>
      </div>

      {/* Visual Comparison */}
      {(report.figma_screenshot_url || report.website_screenshot_url) && (
        <div className="card mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-900">
              Visual Comparison
            </h3>
            {report.figma_screenshot_url && report.website_screenshot_url && !figmaImageError && !websiteImageError && (
              <div className="flex bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('slider')}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                    viewMode === 'slider' 
                      ? 'bg-white text-gray-900 shadow-sm' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Slider
                </button>
                <button
                  onClick={() => setViewMode('sideBySide')}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                    viewMode === 'sideBySide' 
                      ? 'bg-white text-gray-900 shadow-sm' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Side by Side
                </button>
              </div>
            )}
          </div>
          
          {/* Show slider if both images exist and no errors */}
          {report.figma_screenshot_url && report.website_screenshot_url && !figmaImageError && !websiteImageError && viewMode === 'slider' ? (
            <>
              <div className="rounded-lg overflow-hidden border-2 border-gray-200">
                <ReactCompareSlider
                  itemOne={
                    <ReactCompareSliderImage
                      src={report.figma_screenshot_url}
                      alt="Figma Design"
                      onError={() => setFigmaImageError(true)}
                    />
                  }
                  itemTwo={
                    <ReactCompareSliderImage
                      src={report.website_screenshot_url}
                      alt="Website"
                      onError={() => setWebsiteImageError(true)}
                    />
                  }
                  style={{
                    width: '100%',
                    height: 'auto',
                  }}
                />
              </div>
              <div className="flex justify-between text-sm text-gray-600 mt-2">
                <span>← Figma Design</span>
                <span>Website →</span>
              </div>
            </>
          ) : (
            /* Show side-by-side view */
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-lg overflow-hidden border-2 border-gray-200">
                <div className="bg-gradient-to-r from-purple-500 to-pink-500 px-4 py-2">
                  <span className="text-sm font-medium text-white">Figma Design</span>
                </div>
                {report.figma_screenshot_url && !figmaImageError ? (
                  <img 
                    src={report.figma_screenshot_url} 
                    alt="Figma Design" 
                    className="w-full h-auto"
                    onError={() => setFigmaImageError(true)}
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center h-64 bg-gray-50">
                    <ImageOff className="w-12 h-12 text-gray-300 mb-2" />
                    <span className="text-gray-400">
                      {figmaImageError ? 'Failed to load image' : 'No screenshot available'}
                    </span>
                  </div>
                )}
              </div>
              <div className="rounded-lg overflow-hidden border-2 border-gray-200">
                <div className="bg-gradient-to-r from-emerald-500 to-teal-500 px-4 py-2">
                  <span className="text-sm font-medium text-white">Website</span>
                </div>
                {report.website_screenshot_url && !websiteImageError ? (
                  <img 
                    src={report.website_screenshot_url} 
                    alt="Website" 
                    className="w-full h-auto"
                    onError={() => setWebsiteImageError(true)}
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center h-64 bg-gray-50">
                    <ImageOff className="w-12 h-12 text-gray-300 mb-2" />
                    <span className="text-gray-400">
                      {websiteImageError ? 'Failed to load image' : 'No screenshot available'}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Differences List */}
      {report.differences && report.differences.length > 0 && (
        <DiffViewer differences={report.differences} />
      )}
    </div>
  )
}
