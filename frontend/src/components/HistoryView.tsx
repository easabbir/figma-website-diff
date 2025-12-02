import { useState, useEffect } from 'react'
import { Clock, Trash2, ExternalLink, AlertCircle, AlertTriangle, X, Search, BarChart3, Globe, TrendingUp, Layers } from 'lucide-react'
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
    
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden'
    
    return () => {
      // Re-enable body scroll when modal closes
      document.body.style.overflow = 'unset'
    }
  }, [])

  const fetchHistory = async () => {
    try {
      const response = await axios.get('/api/v1/history?limit=50&status=completed')
      // Filter out failed comparisons (0% match score with no differences usually means error)
      const successfulItems = response.data.items.filter(
        (item: HistoryItem) => item.status === 'completed' && item.match_score > 0
      )
      setHistory(successfulItems)
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
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[85vh] overflow-hidden border border-gray-100">
        {/* Header */}
        <div className="bg-gradient-to-r from-violet-600 via-purple-600 to-indigo-600 text-white p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-2.5 bg-white/10 backdrop-blur-sm rounded-xl border border-white/20">
                <Clock className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-xl font-bold">Comparison History</h2>
                <p className="text-white/70 text-sm">View and manage past comparisons</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Stats */}
        {stats && stats.total_comparisons > 0 && (
          <div className="grid grid-cols-4 gap-3 p-4 bg-gradient-to-b from-gray-50 to-white border-b border-gray-100">
            <div className="bg-white rounded-xl p-3 border border-gray-100 shadow-sm text-center">
              <div className="flex items-center justify-center gap-2 mb-1">
                <Layers className="w-4 h-4 text-violet-500" />
                <p className="text-xl font-bold text-gray-900">{stats.total_comparisons}</p>
              </div>
              <p className="text-xs text-gray-500">Total Comparisons</p>
            </div>
            <div className="bg-white rounded-xl p-3 border border-gray-100 shadow-sm text-center">
              <div className="flex items-center justify-center gap-2 mb-1">
                <TrendingUp className="w-4 h-4 text-emerald-500" />
                <p className={`text-xl font-bold ${getScoreColor(stats.avg_match_score)}`}>
                  {stats.avg_match_score.toFixed(1)}%
                </p>
              </div>
              <p className="text-xs text-gray-500">Avg Match Score</p>
            </div>
            <div className="bg-white rounded-xl p-3 border border-gray-100 shadow-sm text-center">
              <div className="flex items-center justify-center gap-2 mb-1">
                <BarChart3 className="w-4 h-4 text-orange-500" />
                <p className="text-xl font-bold text-orange-600">{stats.total_differences_found}</p>
              </div>
              <p className="text-xs text-gray-500">Total Differences</p>
            </div>
            <div className="bg-white rounded-xl p-3 border border-gray-100 shadow-sm text-center">
              <div className="flex items-center justify-center gap-2 mb-1">
                <Globe className="w-4 h-4 text-blue-500" />
                <p className="text-xl font-bold text-blue-600">{stats.unique_websites}</p>
              </div>
              <p className="text-xs text-gray-500">Unique Websites</p>
            </div>
          </div>
        )}

        {/* Search & Delete All */}
        <div className="p-4 border-b border-gray-100 flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by website URL or project name..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:bg-white focus:border-violet-500 focus:ring-1 focus:ring-violet-500 transition-all text-sm"
            />
          </div>
          {history.length > 0 && (
            confirmDeleteAll ? (
              <div className="flex items-center gap-2 bg-red-50 rounded-xl px-3 py-1 border border-red-100">
                <span className="text-sm text-red-600 font-medium">Delete all?</span>
                <button
                  onClick={handleDeleteAll}
                  disabled={deletingAll}
                  className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
                >
                  {deletingAll ? 'Deleting...' : 'Yes'}
                </button>
                <button
                  onClick={() => setConfirmDeleteAll(false)}
                  className="px-3 py-1.5 bg-white hover:bg-gray-100 text-gray-700 text-sm font-medium rounded-lg transition-colors border border-gray-200"
                >
                  No
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmDeleteAll(true)}
                className="px-4 py-2.5 bg-red-50 hover:bg-red-100 text-red-600 text-sm font-medium rounded-xl transition-colors flex items-center gap-2 border border-red-100"
              >
                <Trash2 className="w-4 h-4" />
                Delete All
              </button>
            )
          )}
        </div>

        {/* History List */}
        <div className="overflow-y-auto max-h-[45vh]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-violet-600 border-t-transparent"></div>
            </div>
          ) : filteredHistory.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Clock className="w-8 h-8 text-gray-400" />
              </div>
              <p className="font-medium text-gray-900">No comparison history found</p>
              <p className="text-sm text-gray-500 mt-1">Run your first comparison to see it here!</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filteredHistory.map((item) => (
                <div
                  key={item.id}
                  className="p-4 hover:bg-gray-50/50 transition-colors group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className={`text-lg font-bold ${getScoreColor(item.match_score)}`}>
                          {item.match_score.toFixed(1)}%
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          item.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                          item.status === 'failed' ? 'bg-red-100 text-red-700' :
                          'bg-amber-100 text-amber-700'
                        }`}>
                          {item.status}
                        </span>
                        {item.project_name && (
                          <span className="px-2 py-0.5 bg-violet-100 text-violet-700 rounded-full text-xs font-medium">
                            {item.project_name}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-900 truncate font-medium">{item.website_url}</p>
                      <div className="flex items-center gap-4 mt-1.5 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDate(item.created_at)}
                        </span>
                        <span className="px-2 py-0.5 bg-gray-100 rounded-full">
                          {item.viewport_name} ({item.viewport_width}x{item.viewport_height})
                        </span>
                        <span className="flex items-center gap-1 text-red-600">
                          <AlertCircle className="w-3 h-3" />
                          {item.critical_count}
                        </span>
                        <span className="flex items-center gap-1 text-amber-600">
                          <AlertTriangle className="w-3 h-3" />
                          {item.warning_count}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 ml-4">
                      <button
                        onClick={() => onSelectJob(item.job_id)}
                        className="p-2 text-violet-600 hover:bg-violet-50 rounded-lg transition-colors"
                        title="View Report"
                      >
                        <ExternalLink className="w-5 h-5" />
                      </button>
                      
                      {confirmDeleteId === item.job_id ? (
                        <div className="flex items-center gap-1 bg-red-50 rounded-lg px-2 py-1 border border-red-100">
                          <span className="text-xs text-red-700 font-medium">Delete?</span>
                          <button
                            onClick={() => confirmDelete(item.job_id)}
                            disabled={deletingId === item.job_id}
                            className="p-1 text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors disabled:opacity-50"
                            title="Confirm Delete"
                          >
                            {deletingId === item.job_id ? (
                              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : (
                              <Trash2 className="w-3.5 h-3.5" />
                            )}
                          </button>
                          <button
                            onClick={cancelDelete}
                            className="p-1 text-gray-600 hover:bg-white rounded-md transition-colors"
                            title="Cancel"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleDeleteClick(item.job_id)}
                          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
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
