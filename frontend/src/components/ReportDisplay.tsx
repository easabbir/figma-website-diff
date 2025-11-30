import { useState, useEffect } from 'react'
import { ArrowLeft, Download, CheckCircle, AlertCircle, Info, Loader2, FileText } from 'lucide-react'
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

export default function ReportDisplay({ jobId, onBack }: ReportDisplayProps) {
  const [report, setReport] = useState<DiffReport | null>(null)
  const [progress, setProgress] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let progressInterval: ReturnType<typeof setInterval>

    const fetchProgress = async () => {
      try {
        const response = await axios.get(`/api/v1/progress/${jobId}`)
        setProgress(response.data.progress)
        console.log('Progress update:', response.data.status, response.data.progress + '%', response.data.message)

        if (response.data.status === 'completed' || response.data.status === 'failed') {
          clearInterval(progressInterval)
          fetchReport()
        }
      } catch (err: any) {
        console.error('Error fetching progress:', err)
        clearInterval(progressInterval)
        setError(`Failed to fetch progress: ${err.message}`)
        setLoading(false)
      }
    }

    const fetchReport = async () => {
      try {
        const response = await axios.get(`/api/v1/report/${jobId}`)
        
        // Only process if we got a complete report (status 200)
        console.log('Report response:', response.data)
        console.log('Summary:', response.data.summary)
        
        setReport(response.data)
        setLoading(false)

        if (response.data.status === 'failed') {
          setError(response.data.error || 'Comparison failed')
          toast.error('Comparison failed')
        } else {
          toast.success('Comparison completed!')
        }
      } catch (err: any) {
        if (err.response?.status === 202) {
          // Still processing - this shouldn't happen since we only call after progress shows complete
          console.log('Unexpected 202 response when fetching report')
          return
        }
        console.error('Error fetching report:', err)
        setError('Failed to load report')
        setLoading(false)
      }
    }

    // Poll for progress only - report will be fetched when progress shows completion
    progressInterval = setInterval(fetchProgress, 1000)

    // Initial fetch
    fetchProgress()

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
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card text-center py-12">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Error</h2>
          <p className="text-gray-600 mb-6">{error || 'Failed to load report'}</p>
          <button onClick={onBack} className="btn-primary">
            Go Back
          </button>
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
      {report.figma_screenshot_url && report.website_screenshot_url && (
        <div className="card mb-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">
            Visual Comparison
          </h3>
          <div className="rounded-lg overflow-hidden border-2 border-gray-200">
            <ReactCompareSlider
              itemOne={
                <ReactCompareSliderImage
                  src={report.figma_screenshot_url}
                  alt="Figma Design"
                />
              }
              itemTwo={
                <ReactCompareSliderImage
                  src={report.website_screenshot_url}
                  alt="Website"
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
        </div>
      )}

      {/* Differences List */}
      {report.differences && report.differences.length > 0 && (
        <DiffViewer differences={report.differences} />
      )}
    </div>
  )
}
