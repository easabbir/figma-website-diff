import { useState, useEffect, useRef, useCallback } from 'react'
import { ArrowLeft, Download, CheckCircle, AlertCircle, Info, Loader2, FileText, ImageOff, Layers, Sparkles, SplitSquareHorizontal } from 'lucide-react'
import axios from 'axios'
import { toast } from 'react-toastify'
import {
  ReactCompareSlider,
  ReactCompareSliderImage
} from 'react-compare-slider'
import DiffViewer from './DiffViewer'
import { useAuth } from '../context/AuthContext'

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
  const { refreshUser } = useAuth()
  const [report, setReport] = useState<DiffReport | null>(null)
  const [progress, setProgress] = useState(0)
  const [displayProgress, setDisplayProgress] = useState(0)  // Smoothed progress for display
  const [progressMessage, setProgressMessage] = useState('Initializing...')
  const [currentStep, setCurrentStep] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'slider' | 'sideBySide' | 'overlay' | 'difference' | 'split'>('slider')
  const [splitPosition, setSplitPosition] = useState(50)
  const splitContainerRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [overlayOpacity, setOverlayOpacity] = useState(50)
  const [diffLoading, setDiffLoading] = useState(false)
  const [diffThreshold, setDiffThreshold] = useState(30)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [figmaImageError, setFigmaImageError] = useState(false)
  const [websiteImageError, setWebsiteImageError] = useState(false)
  const [toastShown, setToastShown] = useState(false)

  // Compute pixel difference between two images
  const computeDifference = useCallback((figmaUrl: string, websiteUrl: string, threshold: number) => {
    if (!canvasRef.current) return
    
    setDiffLoading(true)
    
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    
    const img1 = new Image()
    const img2 = new Image()
    img1.crossOrigin = 'anonymous'
    img2.crossOrigin = 'anonymous'
    
    let loaded = 0
    
    const onBothLoaded = () => {
      loaded++
      if (loaded < 2) return
      
      // Use the larger dimensions
      const width = Math.max(img1.width, img2.width)
      const height = Math.max(img1.height, img2.height)
      
      canvas.width = width
      canvas.height = height
      
      // Create temporary canvases for each image
      const tempCanvas1 = document.createElement('canvas')
      const tempCanvas2 = document.createElement('canvas')
      tempCanvas1.width = width
      tempCanvas1.height = height
      tempCanvas2.width = width
      tempCanvas2.height = height
      
      const tempCtx1 = tempCanvas1.getContext('2d')
      const tempCtx2 = tempCanvas2.getContext('2d')
      
      if (!tempCtx1 || !tempCtx2) return
      
      // Fill with white background and draw images
      tempCtx1.fillStyle = '#ffffff'
      tempCtx1.fillRect(0, 0, width, height)
      tempCtx1.drawImage(img1, 0, 0)
      
      tempCtx2.fillStyle = '#ffffff'
      tempCtx2.fillRect(0, 0, width, height)
      tempCtx2.drawImage(img2, 0, 0)
      
      // Get image data
      const data1 = tempCtx1.getImageData(0, 0, width, height)
      const data2 = tempCtx2.getImageData(0, 0, width, height)
      const diffData = ctx.createImageData(width, height)
      
      // Compare pixels
      for (let i = 0; i < data1.data.length; i += 4) {
        const r1 = data1.data[i]
        const g1 = data1.data[i + 1]
        const b1 = data1.data[i + 2]
        
        const r2 = data2.data[i]
        const g2 = data2.data[i + 1]
        const b2 = data2.data[i + 2]
        
        // Calculate color difference
        const diff = Math.abs(r1 - r2) + Math.abs(g1 - g2) + Math.abs(b1 - b2)
        
        if (diff > threshold) {
          // Highlight difference in red
          diffData.data[i] = 255      // R
          diffData.data[i + 1] = 60   // G
          diffData.data[i + 2] = 60   // B
          diffData.data[i + 3] = 255  // A
        } else {
          // Show matching areas in grayscale
          const gray = Math.round((r1 + g1 + b1) / 3)
          diffData.data[i] = gray
          diffData.data[i + 1] = gray
          diffData.data[i + 2] = gray
          diffData.data[i + 3] = 255
        }
      }
      
      ctx.putImageData(diffData, 0, 0)
      setDiffLoading(false)
    }
    
    img1.onload = onBothLoaded
    img2.onload = onBothLoaded
    img1.onerror = () => setDiffLoading(false)
    img2.onerror = () => setDiffLoading(false)
    
    img1.src = figmaUrl
    img2.src = websiteUrl
  }, [])

  // Compute difference when view mode changes to 'difference' or threshold changes
  useEffect(() => {
    if (viewMode === 'difference' && report?.figma_screenshot_url && report?.website_screenshot_url) {
      computeDifference(report.figma_screenshot_url, report.website_screenshot_url, diffThreshold)
    }
  }, [viewMode, diffThreshold, report?.figma_screenshot_url, report?.website_screenshot_url, computeDifference])

  // Smooth progress animation - interpolate between actual progress values
  useEffect(() => {
    if (displayProgress < progress) {
      const diff = progress - displayProgress
      const step = Math.max(1, Math.ceil(diff / 10))  // Animate in steps
      const timer = setTimeout(() => {
        setDisplayProgress(prev => Math.min(prev + step, progress))
      }, 50)  // 50ms intervals for smooth animation
      return () => clearTimeout(timer)
    }
  }, [progress, displayProgress])

  useEffect(() => {
    let progressInterval: ReturnType<typeof setInterval>
    let reportFetched = false  // Prevent multiple fetches/toasts

    const fetchProgress = async () => {
      try {
        const response = await axios.get(`/api/v1/progress/${jobId}`)
        setProgress(response.data.progress || 0)
        setProgressMessage(response.data.message || 'Processing...')
        setCurrentStep(response.data.current_step || '')
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
          toast.success('Comparison completed successfully!')
          // Refresh user data to update comparison count
          refreshUser()
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
          {/* Animated Logo */}
          <div className="relative inline-block mb-6">
            <div className="absolute inset-0 bg-primary-400 rounded-full blur-xl opacity-30 animate-pulse" />
            <Loader2 className="w-16 h-16 text-primary-600 animate-spin relative" />
          </div>
          
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Processing Comparison...
          </h2>
          
          {/* Current Step Display */}
          <p className="text-gray-600 mb-2">
            {progressMessage}
          </p>
          {currentStep && (
            <p className="text-sm text-primary-600 font-medium mb-4">
              {currentStep}
            </p>
          )}

          {/* Enhanced Progress Bar */}
          <div className="max-w-md mx-auto">
            <div className="w-full bg-gray-100 rounded-full h-4 mb-3 overflow-hidden shadow-inner">
              <div
                className="h-full rounded-full bg-gradient-to-r from-primary-500 via-primary-600 to-violet-600 relative overflow-hidden"
                style={{ 
                  width: `${displayProgress}%`,
                  transition: 'width 0.3s ease-out'
                }}
              >
                {/* Shimmer effect */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
              </div>
            </div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500">Progress</span>
              <span className="font-semibold text-primary-600">{displayProgress}%</span>
            </div>
          </div>

          {/* Helpful tip */}
          <p className="text-xs text-gray-400 mt-6">
            This may take a minute. Please wait while we analyze your design and website.
          </p>
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
                <button
                  onClick={() => setViewMode('overlay')}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all flex items-center gap-1 ${
                    viewMode === 'overlay' 
                      ? 'bg-white text-gray-900 shadow-sm' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5" />
                  Overlay
                </button>
                <button
                  onClick={() => setViewMode('difference')}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all flex items-center gap-1 ${
                    viewMode === 'difference' 
                      ? 'bg-white text-gray-900 shadow-sm' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Difference
                </button>
                <button
                  onClick={() => setViewMode('split')}
                  className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all flex items-center gap-1 ${
                    viewMode === 'split' 
                      ? 'bg-white text-gray-900 shadow-sm' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <SplitSquareHorizontal className="w-3.5 h-3.5" />
                  Split
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
                      style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top left' }}
                    />
                  }
                  itemTwo={
                    <ReactCompareSliderImage
                      src={report.website_screenshot_url}
                      alt="Website"
                      onError={() => setWebsiteImageError(true)}
                      style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top left' }}
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
          ) : report.figma_screenshot_url && report.website_screenshot_url && !figmaImageError && !websiteImageError && viewMode === 'overlay' ? (
            /* Overlay/Blend View */
            <>
              {/* Opacity Slider Control */}
              <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Blend Opacity</span>
                  <span className="text-sm text-gray-500">{overlayOpacity}%</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-purple-600 font-medium whitespace-nowrap">Figma</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={overlayOpacity}
                    onChange={(e) => setOverlayOpacity(Number(e.target.value))}
                    className="w-full h-2 bg-gradient-to-r from-purple-500 to-emerald-500 rounded-lg appearance-none cursor-pointer slider-thumb"
                  />
                  <span className="text-xs text-emerald-600 font-medium whitespace-nowrap">Website</span>
                </div>
                <p className="text-xs text-gray-400 mt-2 text-center">
                  Drag the slider to blend between Figma design and website screenshot
                </p>
              </div>
              
              {/* Overlay Container */}
              <div className="rounded-lg overflow-hidden border-2 border-gray-200 relative">
                {/* Base Layer - Figma Design */}
                <img
                  src={report.figma_screenshot_url}
                  alt="Figma Design"
                  className="w-full h-auto"
                  onError={() => setFigmaImageError(true)}
                />
                {/* Overlay Layer - Website */}
                <img
                  src={report.website_screenshot_url}
                  alt="Website"
                  className="absolute top-0 left-0 w-full h-full object-cover object-top"
                  style={{ opacity: overlayOpacity / 100 }}
                  onError={() => setWebsiteImageError(true)}
                />
              </div>
              
              {/* Legend */}
              <div className="flex justify-center gap-6 text-sm text-gray-600 mt-3">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                  <span>Figma Design (Base)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                  <span>Website (Overlay)</span>
                </div>
              </div>
            </>
          ) : report.figma_screenshot_url && report.website_screenshot_url && !figmaImageError && !websiteImageError && viewMode === 'difference' ? (
            /* Difference Highlight View */
            <>
              {/* Threshold Control */}
              <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Sensitivity Threshold</span>
                  <span className="text-sm text-gray-500">{diffThreshold}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-gray-500 font-medium whitespace-nowrap">Low</span>
                  <input
                    type="range"
                    min="5"
                    max="100"
                    value={diffThreshold}
                    onChange={(e) => setDiffThreshold(Number(e.target.value))}
                    className="w-full h-2 bg-gradient-to-r from-green-400 to-red-500 rounded-lg appearance-none cursor-pointer slider-thumb"
                  />
                  <span className="text-xs text-gray-500 font-medium whitespace-nowrap">High</span>
                </div>
                <p className="text-xs text-gray-400 mt-2 text-center">
                  Lower values detect more subtle differences, higher values show only major changes
                </p>
              </div>
              
              {/* Difference Canvas Container */}
              <div className="rounded-lg overflow-hidden border-2 border-gray-200 bg-gray-900">
                <canvas
                  ref={canvasRef}
                  className="w-full h-auto"
                  style={{ display: diffLoading ? 'none' : 'block' }}
                />
                {diffLoading && (
                  <div className="flex flex-col items-center justify-center py-20">
                    <Loader2 className="w-8 h-8 text-white animate-spin mb-3" />
                    <span className="text-white text-sm">Computing differences...</span>
                  </div>
                )}
              </div>
              
              {/* Legend */}
              <div className="flex justify-center gap-6 text-sm text-gray-600 mt-3">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500"></div>
                  <span>Differences (Red)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-gray-400"></div>
                  <span>Matching Areas (Gray)</span>
                </div>
              </div>
            </>
          ) : report.figma_screenshot_url && report.website_screenshot_url && !figmaImageError && !websiteImageError && viewMode === 'split' ? (
            /* Split View with draggable divider */
            <>
              {/* Instructions */}
              <div className="mb-4 p-3 bg-gray-50 rounded-lg text-center">
                <p className="text-sm text-gray-600">
                  <span className="font-medium">Drag the divider</span> or use the slider below to compare specific areas
                </p>
              </div>
              
              {/* Split Position Slider */}
              <div className="mb-4 px-4">
                <div className="flex items-center gap-4">
                  <span className="text-xs text-purple-600 font-medium whitespace-nowrap">Figma</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={splitPosition}
                    onChange={(e) => setSplitPosition(Number(e.target.value))}
                    className="w-full h-2 bg-gradient-to-r from-purple-500 to-emerald-500 rounded-lg appearance-none cursor-pointer slider-thumb"
                  />
                  <span className="text-xs text-emerald-600 font-medium whitespace-nowrap">Website</span>
                </div>
              </div>
              
              {/* Split Container */}
              <div 
                ref={splitContainerRef}
                className="rounded-lg overflow-hidden border-2 border-gray-200 relative select-none"
                onMouseDown={() => setIsDragging(true)}
                onMouseUp={() => setIsDragging(false)}
                onMouseLeave={() => setIsDragging(false)}
                onMouseMove={(e) => {
                  if (isDragging && splitContainerRef.current) {
                    const rect = splitContainerRef.current.getBoundingClientRect()
                    const x = e.clientX - rect.left
                    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100))
                    setSplitPosition(percentage)
                  }
                }}
              >
                {/* Figma Image (Left side) */}
                <div 
                  className="absolute top-0 left-0 h-full overflow-hidden"
                  style={{ width: `${splitPosition}%` }}
                >
                  <img
                    src={report.figma_screenshot_url}
                    alt="Figma Design"
                    className="h-full object-cover object-left"
                    style={{ width: `${100 / (splitPosition / 100)}%`, maxWidth: 'none' }}
                    onError={() => setFigmaImageError(true)}
                    draggable={false}
                  />
                </div>
                
                {/* Website Image (Full width, behind) */}
                <img
                  src={report.website_screenshot_url}
                  alt="Website"
                  className="w-full h-auto"
                  onError={() => setWebsiteImageError(true)}
                  draggable={false}
                />
                
                {/* Divider Line */}
                <div 
                  className="absolute top-0 bottom-0 w-1 bg-white shadow-lg cursor-ew-resize z-10"
                  style={{ left: `${splitPosition}%`, transform: 'translateX(-50%)' }}
                >
                  {/* Divider Handle */}
                  <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center border-2 border-gray-300">
                    <div className="flex gap-0.5">
                      <div className="w-0.5 h-4 bg-gray-400 rounded"></div>
                      <div className="w-0.5 h-4 bg-gray-400 rounded"></div>
                    </div>
                  </div>
                </div>
                
                {/* Labels */}
                <div className="absolute top-2 left-2 bg-purple-600 text-white text-xs px-2 py-1 rounded shadow">
                  Figma
                </div>
                <div className="absolute top-2 right-2 bg-emerald-600 text-white text-xs px-2 py-1 rounded shadow">
                  Website
                </div>
              </div>
              
              {/* Position indicator */}
              <div className="flex justify-center text-sm text-gray-500 mt-2">
                <span>Split: {Math.round(splitPosition)}% Figma / {Math.round(100 - splitPosition)}% Website</span>
              </div>
            </>
          ) : viewMode === 'sideBySide' || figmaImageError || websiteImageError ? (
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
          ) : null}
        </div>
      )}

      {/* Differences List */}
      {report.differences && report.differences.length > 0 && (
        <DiffViewer differences={report.differences} />
      )}
    </div>
  )
}
