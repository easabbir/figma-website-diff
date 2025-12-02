import { useState, useEffect } from 'react'
import { Clock, Trash2, ExternalLink, AlertCircle, Info } from 'lucide-react'
import axios from 'axios'
import { toast } from 'react-toastify'

interface HistoryItem {
  id: string
  job_id: string
  figma_url?: string
  website_url: string
  viewport_name: string
  viewport_width: number
  viewport_height: number
  match_score: number
  total_differences: number
  critical_count: number
  warning_count: number
  info_count: number
  status: string
  project_name?: string
  created_at: string
  completed_at?: string
}

interface HistoryStats {
  total_comparisons: number
  avg_match_score: number
  total_differences_found: number
  unique_websites: number
}

interface HistoryViewProps {
  onSelectJob: (jobId: string) => void
  onClose: () => void
}

export default function HistoryView({ onSelectJob, onClose }: HistoryViewProps) {
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [stats, setStats] = useState<HistoryStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false)
  const [deletingAll, setDeletingAll] = useState(false)

  useEffect(() => {
    fetchHistory()
    fetchStats()
  }, [])

  const fetchHistory = async () => {
    try {
      const response = await axios.get('/api/v1/history?limit=50')
      setHistory(response.data.items)
    } catch (err) {
      console.error('Failed to fetch history:', err)
      toast.error('Failed to load comparison history')
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await axios.get('/api/v1/history/stats')
      setStats(response.data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  const handleDeleteClick = (jobId: string) => {
    setConfirmDeleteId(jobId)
  }

  const cancelDelete = () => {
    setConfirmDeleteId(null)
  }

  const confirmDelete = async (jobId: string) => {
    setDeletingId(jobId)
    try {
      await axios.delete(`/api/v1/history/${jobId}`)
      setHistory(history.filter(item => item.job_id !== jobId))
      toast.success('Comparison deleted')
    } catch (err) {
      toast.error('Failed to delete comparison')
    } finally {
      setDeletingId(null)
      setConfirmDeleteId(null)
    }
  }

  const handleDeleteAll = async () => {
    setDeletingAll(true)
    try {
      await axios.delete('/api/v1/history')
      setHistory([])
      setStats(null)
      toast.success('All history deleted')
    } catch (err) {
      toast.error('Failed to delete history')
    } finally {
      setDeletingAll(false)
      setConfirmDeleteAll(false)
    }
  }

  const formatDate = (dateString: string) => {
    // Ensure UTC timestamp is properly converted to local time
    const date = new Date(dateString.endsWith('Z') ? dateString : dateString + 'Z')
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const filteredHistory = history.filter(item =>
    item.website_url.toLowerCase().includes(filter.toLowerCase()) ||
    (item.project_name?.toLowerCase().includes(filter.toLowerCase()))
  )

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-primary-600 to-primary-700 text-white p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Clock className="w-8 h-8" />
              <div>
                <h2 className="text-2xl font-bold">Comparison History</h2>
                <p className="text-primary-100">View and manage past comparisons</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:bg-white/20 rounded-lg p-2 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Stats */}
        {stats && stats.total_comparisons > 0 && (
          <div className="grid grid-cols-4 gap-4 p-4 bg-gray-50 border-b">
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.total_comparisons}</p>
              <p className="text-sm text-gray-600">Total Comparisons</p>
            </div>
            <div className="text-center">
              <p className={`text-2xl font-bold ${getScoreColor(stats.avg_match_score)}`}>
                {stats.avg_match_score.toFixed(1)}%
              </p>
              <p className="text-sm text-gray-600">Avg Match Score</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-orange-600">{stats.total_differences_found}</p>
              <p className="text-sm text-gray-600">Total Differences</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">{stats.unique_websites}</p>
              <p className="text-sm text-gray-600">Unique Websites</p>
            </div>
          </div>
        )}

        {/* Search & Delete All */}
        <div className="p-4 border-b flex gap-3">
          <input
            type="text"
            placeholder="Search by website URL or project name..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          {history.length > 0 && (
            confirmDeleteAll ? (
              <div className="flex items-center gap-2 animate-fadeIn">
                <span className="text-sm text-red-600 font-medium">Delete all?</span>
                <button
                  onClick={handleDeleteAll}
                  disabled={deletingAll}
                  className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
                >
                  {deletingAll ? 'Deleting...' : 'Yes'}
                </button>
                <button
                  onClick={() => setConfirmDeleteAll(false)}
                  className="px-3 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 text-sm font-medium rounded-lg transition-colors"
                >
                  No
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmDeleteAll(true)}
                className="px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                Delete All
              </button>
            )
          )}
        </div>

        {/* History List */}
        <div className="overflow-y-auto max-h-[50vh]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : filteredHistory.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Clock className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="font-medium">No comparison history found</p>
              <p className="text-sm mt-2">Run your first comparison to see it here!</p>
            </div>
          ) : (
            <div className="divide-y">
              {filteredHistory.map((item) => (
                <div
                  key={item.id}
                  className="p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-lg font-bold ${getScoreColor(item.match_score)}`}>
                          {item.match_score.toFixed(1)}%
                        </span>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          item.status === 'completed' ? 'bg-green-100 text-green-700' :
                          item.status === 'failed' ? 'bg-red-100 text-red-700' :
                          'bg-yellow-100 text-yellow-700'
                        }`}>
                          {item.status}
                        </span>
                        {item.project_name && (
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                            {item.project_name}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-900 truncate">{item.website_url}</p>
                      <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                        <span>{formatDate(item.created_at)}</span>
                        <span>{item.viewport_name} ({item.viewport_width}x{item.viewport_height})</span>
                        <span className="flex items-center gap-1">
                          <AlertCircle className="w-3 h-3 text-red-500" />
                          {item.critical_count}
                        </span>
                        <span className="flex items-center gap-1">
                          <Info className="w-3 h-3 text-yellow-500" />
                          {item.warning_count}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      <button
                        onClick={() => onSelectJob(item.job_id)}
                        className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                        title="View Report"
                      >
                        <ExternalLink className="w-5 h-5" />
                      </button>
                      
                      {confirmDeleteId === item.job_id ? (
                        <div className="flex items-center gap-1 bg-red-50 rounded-lg px-2 py-1 animate-fadeIn">
                          <span className="text-xs text-red-700 font-medium">Delete?</span>
                          <button
                            onClick={() => confirmDelete(item.job_id)}
                            disabled={deletingId === item.job_id}
                            className="p-1 text-white bg-red-600 hover:bg-red-700 rounded transition-colors disabled:opacity-50"
                            title="Confirm Delete"
                          >
                            {deletingId === item.job_id ? (
                              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : (
                              <Trash2 className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            onClick={cancelDelete}
                            className="p-1 text-gray-600 hover:bg-gray-200 rounded transition-colors"
                            title="Cancel"
                          >
                            <span className="text-xs font-bold">✕</span>
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleDeleteClick(item.job_id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
