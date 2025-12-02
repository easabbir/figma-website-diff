import { useState, useEffect } from 'react'
import { Play, Figma, Globe, Settings, Clock, Sparkles, Palette, Ruler, Type, ChevronDown, ChevronUp, Zap } from 'lucide-react'
import { toast } from 'react-toastify'
import axios from 'axios'
import FigmaOAuth from './FigmaOAuth'

interface CachedFormData {
  figmaUrl: string
  figmaToken: string
  figmaNodeId?: string
  websiteUrl: string
  viewportWidth: string
  viewportHeight: string
  comparisonMode: string
}

interface ComparisonFormProps {
  onComparisonStart: (result: { jobId: string; status: string }, formData: CachedFormData) => void
  cachedData: CachedFormData | null
  onShowHistory?: () => void
}

export default function ComparisonForm({ onComparisonStart, cachedData, onShowHistory }: ComparisonFormProps) {
  const [figmaUrl, setFigmaUrl] = useState(cachedData?.figmaUrl || '')
  const [figmaToken, setFigmaToken] = useState(cachedData?.figmaToken || '')
  const [figmaNodeId, setFigmaNodeId] = useState(cachedData?.figmaNodeId || '')
  const [websiteUrl, setWebsiteUrl] = useState(cachedData?.websiteUrl || '')
  const [viewportWidth, setViewportWidth] = useState(cachedData?.viewportWidth || '1920')
  const [viewportHeight, setViewportHeight] = useState(cachedData?.viewportHeight || '1080')
  const [comparisonMode, setComparisonMode] = useState(cachedData?.comparisonMode || 'hybrid')
  const [loading, setLoading] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [hasOAuthToken, setHasOAuthToken] = useState(false)
  const [useOAuth, setUseOAuth] = useState(true)

  // Extract node ID from Figma URL
  const extractNodeIdFromUrl = (url: string): string => {
    try {
      const urlObj = new URL(url)
      const nodeId = urlObj.searchParams.get('node-id')
      return nodeId || ''
    } catch {
      return ''
    }
  }

  // Auto-extract node ID when URL changes
  useEffect(() => {
    if (figmaUrl) {
      const extractedNodeId = extractNodeIdFromUrl(figmaUrl)
      // Always update node ID when URL changes (even if there's an existing one)
      setFigmaNodeId(extractedNodeId)
    } else {
      // Clear node ID when URL is cleared
      setFigmaNodeId('')
    }
  }, [figmaUrl])

  // Restore cached data when it changes
  useEffect(() => {
    if (cachedData) {
      setFigmaUrl(cachedData.figmaUrl)
      setFigmaToken(cachedData.figmaToken)
      setFigmaNodeId(cachedData.figmaNodeId || '')
      setWebsiteUrl(cachedData.websiteUrl)
      setViewportWidth(cachedData.viewportWidth)
      setViewportHeight(cachedData.viewportHeight)
      setComparisonMode(cachedData.comparisonMode)
    }
  }, [cachedData])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Check if we have OAuth token or personal token
    const needsToken = !hasOAuthToken || !useOAuth
    if (!figmaUrl || (needsToken && !figmaToken) || !websiteUrl) {
      toast.error('Please fill in all required fields')
      return
    }

    setLoading(true)

    try {
      // Get the access token - either from OAuth or personal token
      let accessToken = figmaToken
      if (hasOAuthToken && useOAuth) {
        try {
          const tokenResponse = await axios.get('/api/v1/oauth/token')
          accessToken = tokenResponse.data.access_token
        } catch (err) {
          // Fall back to personal token if OAuth fails
          if (!figmaToken) {
            toast.error('OAuth token expired. Please reconnect or use a personal token.')
            setLoading(false)
            return
          }
        }
      }

      const response = await axios.post('/api/v1/compare', {
        figma_input: {
          type: 'url',
          value: figmaUrl,
          access_token: accessToken,
          node_id: figmaNodeId || undefined,
        },
        website_url: websiteUrl,
        options: {
          viewport: {
            width: parseInt(viewportWidth),
            height: parseInt(viewportHeight),
          },
          comparison_mode: comparisonMode,
          tolerance: {
            color: 5,
            spacing: 2,
            dimension: 2,
          },
          include_screenshots: true,
          generate_html_report: true,
        },
      })

      // Don't show success toast here - wait for actual completion in ReportDisplay
      onComparisonStart(
        {
          jobId: response.data.job_id,
          status: response.data.status,
        },
        {
          figmaUrl,
          figmaToken,
          figmaNodeId,
          websiteUrl,
          viewportWidth,
          viewportHeight,
          comparisonMode,
        }
      )
    } catch (error: any) {
      console.error('Error starting comparison:', error)
      toast.error(error.response?.data?.detail || 'Failed to start comparison')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Hero Section */}
      <div className="text-center mb-8">
        <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-3">
          Compare Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-purple-600">Design</span> to Reality
        </h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Instantly detect visual inconsistencies between your Figma designs and live website implementation
        </p>
      </div>

      {/* Main Form Card */}
      <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
        {/* Card Header */}
        <div className="bg-gradient-to-r from-primary-600 via-primary-700 to-purple-700 px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white/20 rounded-lg backdrop-blur-sm">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-white">New Comparison</h2>
                <p className="text-primary-100 text-sm">Enter your design and website details</p>
              </div>
            </div>
            {onShowHistory && (
              <button
                type="button"
                onClick={onShowHistory}
                className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-all border border-white/20"
              >
                <Clock className="w-4 h-4" />
                <span className="font-medium">History</span>
              </button>
            )}
          </div>
        </div>

        <div className="p-6 md:p-8">
          {cachedData && (
            <div className="mb-6 px-4 py-3 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl flex items-center gap-3">
              <div className="p-1.5 bg-blue-100 rounded-lg">
                <Sparkles className="w-4 h-4 text-blue-600" />
              </div>
              <span className="text-sm text-blue-700 font-medium">Previous inputs restored automatically</span>
            </div>
          )}

          {/* OAuth Section */}
          <div className="mb-8 p-4 bg-gradient-to-r from-gray-50 to-slate-50 rounded-xl border border-gray-200">
            <FigmaOAuth onTokenChange={setHasOAuthToken} />
          </div>

          <form onSubmit={handleSubmit} className="space-y-8">
            {/* Figma Input Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2.5 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl shadow-lg shadow-purple-200">
                  <Figma className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Figma Design</h3>
                  <p className="text-xs text-gray-500">Paste your Figma file or frame URL</p>
                </div>
              </div>
              
              <div className="relative">
                <input
                  type="url"
                  value={figmaUrl}
                  onChange={(e) => setFigmaUrl(e.target.value)}
                  placeholder="https://www.figma.com/design/ABC123/Design-Name?node-id=123-456"
                  className="w-full px-4 py-3.5 bg-gray-50 border-2 border-gray-200 rounded-xl focus:border-primary-500 focus:bg-white focus:ring-4 focus:ring-primary-100 transition-all outline-none text-gray-900 placeholder-gray-400"
                  required
                />
              </div>
              
              {/* Node ID input */}
              <div className="pl-4 border-l-2 border-gray-200">
                <label className="text-sm font-medium text-gray-600 mb-2 block flex items-center gap-2">
                  <span>Frame/Node ID</span>
                  <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded-full">Recommended for large files</span>
                </label>
                <input
                  type="text"
                  value={figmaNodeId}
                  onChange={(e) => setFigmaNodeId(e.target.value)}
                  placeholder="e.g., 4614-49797 (auto-extracted from URL)"
                  className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-200 rounded-xl focus:border-primary-500 focus:bg-white focus:ring-4 focus:ring-primary-100 transition-all outline-none text-gray-900 placeholder-gray-400 text-sm"
                />
                <p className="text-xs text-gray-500 mt-2 flex items-start gap-1.5">
                  <span className="text-amber-500">💡</span>
                  <span>Specify a node ID to compare only that frame. Auto-extracted from URL if present.</span>
                </p>
              </div>
              
              {/* Token input */}
              {hasOAuthToken ? (
                <div className="space-y-3 pl-4 border-l-2 border-gray-200">
                  <label className="flex items-center gap-3 cursor-pointer group">
                    <div className="relative">
                      <input
                        type="checkbox"
                        id="useOAuth"
                        checked={useOAuth}
                        onChange={(e) => setUseOAuth(e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-10 h-6 bg-gray-200 rounded-full peer-checked:bg-primary-600 transition-colors"></div>
                      <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full shadow peer-checked:translate-x-4 transition-transform"></div>
                    </div>
                    <span className="text-sm text-gray-700 group-hover:text-gray-900">
                      Use OAuth token <span className="text-green-600 font-medium">(Connected ✓)</span>
                    </span>
                  </label>
                  {!useOAuth && (
                    <input
                      type="text"
                      value={figmaToken}
                      onChange={(e) => setFigmaToken(e.target.value)}
                      placeholder="Figma API Token (personal token)"
                      className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-200 rounded-xl focus:border-primary-500 focus:bg-white focus:ring-4 focus:ring-primary-100 transition-all outline-none text-gray-900 placeholder-gray-400"
                      required
                    />
                  )}
                </div>
              ) : (
                <div className="pl-4 border-l-2 border-gray-200">
                  <input
                    type="text"
                    value={figmaToken}
                    onChange={(e) => setFigmaToken(e.target.value)}
                    placeholder="Figma API Token"
                    className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-200 rounded-xl focus:border-primary-500 focus:bg-white focus:ring-4 focus:ring-primary-100 transition-all outline-none text-gray-900 placeholder-gray-400"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-2">
                    Get your token from{' '}
                    <a
                      href="https://www.figma.com/developers/api#access-tokens"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:text-primary-700 font-medium hover:underline"
                    >
                      Figma Developers
                    </a>
                    {' '}or connect with OAuth above.
                  </p>
                </div>
              )}
            </div>

            {/* Divider */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200"></div>
              </div>
              <div className="relative flex justify-center">
                <span className="px-4 bg-white text-gray-400 text-sm">compare with</span>
              </div>
            </div>

            {/* Website Input Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2.5 bg-gradient-to-br from-emerald-500 to-teal-500 rounded-xl shadow-lg shadow-emerald-200">
                  <Globe className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Website URL</h3>
                  <p className="text-xs text-gray-500">Enter the live website to compare against</p>
                </div>
              </div>
              
              <input
                type="url"
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                placeholder="https://example.com"
                className="w-full px-4 py-3.5 bg-gray-50 border-2 border-gray-200 rounded-xl focus:border-emerald-500 focus:bg-white focus:ring-4 focus:ring-emerald-100 transition-all outline-none text-gray-900 placeholder-gray-400"
                required
              />
            </div>

            {/* Advanced Settings */}
            <div className="border border-gray-200 rounded-xl overflow-hidden">
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Settings className="w-5 h-5 text-gray-500" />
                  <span className="font-medium text-gray-700">Advanced Settings</span>
                </div>
                {showAdvanced ? (
                  <ChevronUp className="w-5 h-5 text-gray-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-400" />
                )}
              </button>

              {showAdvanced && (
                <div className="p-4 bg-white border-t border-gray-200 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-gray-700 mb-2 block">
                        Viewport Width
                      </label>
                      <input
                        type="number"
                        value={viewportWidth}
                        onChange={(e) => setViewportWidth(e.target.value)}
                        className="w-full px-4 py-2.5 bg-gray-50 border-2 border-gray-200 rounded-lg focus:border-primary-500 focus:bg-white transition-all outline-none"
                        min="320"
                        max="3840"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700 mb-2 block">
                        Viewport Height
                      </label>
                      <input
                        type="number"
                        value={viewportHeight}
                        onChange={(e) => setViewportHeight(e.target.value)}
                        className="w-full px-4 py-2.5 bg-gray-50 border-2 border-gray-200 rounded-lg focus:border-primary-500 focus:bg-white transition-all outline-none"
                        min="240"
                        max="2160"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Comparison Mode
                    </label>
                    <select
                      value={comparisonMode}
                      onChange={(e) => setComparisonMode(e.target.value)}
                      className="w-full px-4 py-2.5 bg-gray-50 border-2 border-gray-200 rounded-lg focus:border-primary-500 focus:bg-white transition-all outline-none cursor-pointer"
                    >
                      <option value="hybrid">Hybrid (Recommended)</option>
                      <option value="structural">Structural Only</option>
                      <option value="visual">Visual Only</option>
                    </select>
                  </div>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 bg-gradient-to-r from-primary-600 to-purple-600 hover:from-primary-700 hover:to-purple-700 text-white font-semibold rounded-xl shadow-lg shadow-primary-200 hover:shadow-xl hover:shadow-primary-300 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3 group"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <Play className="w-5 h-5 group-hover:scale-110 transition-transform" />
                  <span>Start Comparison</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-8">
        <div className="group bg-white rounded-xl p-5 border border-gray-200 hover:border-primary-200 hover:shadow-lg hover:shadow-primary-100/50 transition-all">
          <div className="w-12 h-12 bg-gradient-to-br from-pink-500 to-rose-500 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-lg shadow-pink-200">
            <Palette className="w-6 h-6 text-white" />
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">Color Analysis</h3>
          <p className="text-sm text-gray-600 leading-relaxed">
            Detects color inconsistencies and brand guideline violations with precision
          </p>
        </div>
        <div className="group bg-white rounded-xl p-5 border border-gray-200 hover:border-primary-200 hover:shadow-lg hover:shadow-primary-100/50 transition-all">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-500 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-lg shadow-blue-200">
            <Ruler className="w-6 h-6 text-white" />
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">Spacing & Layout</h3>
          <p className="text-sm text-gray-600 leading-relaxed">
            Identifies spacing, alignment, and dimension differences automatically
          </p>
        </div>
        <div className="group bg-white rounded-xl p-5 border border-gray-200 hover:border-primary-200 hover:shadow-lg hover:shadow-primary-100/50 transition-all">
          <div className="w-12 h-12 bg-gradient-to-br from-amber-500 to-orange-500 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-lg shadow-amber-200">
            <Type className="w-6 h-6 text-white" />
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">Typography</h3>
          <p className="text-sm text-gray-600 leading-relaxed">
            Compares fonts, sizes, weights, and text properties across designs
          </p>
        </div>
      </div>
    </div>
  )
}
