import { useState, useEffect } from 'react'
import { Play, Figma, Globe, Settings, Clock } from 'lucide-react'
import { toast } from 'react-toastify'
import axios from 'axios'
import FigmaOAuth from './FigmaOAuth'

interface CachedFormData {
  figmaUrl: string
  figmaToken: string
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
  const [websiteUrl, setWebsiteUrl] = useState(cachedData?.websiteUrl || '')
  const [viewportWidth, setViewportWidth] = useState(cachedData?.viewportWidth || '1920')
  const [viewportHeight, setViewportHeight] = useState(cachedData?.viewportHeight || '1080')
  const [comparisonMode, setComparisonMode] = useState(cachedData?.comparisonMode || 'hybrid')
  const [loading, setLoading] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [hasOAuthToken, setHasOAuthToken] = useState(false)
  const [useOAuth, setUseOAuth] = useState(true)

  // Restore cached data when it changes
  useEffect(() => {
    if (cachedData) {
      setFigmaUrl(cachedData.figmaUrl)
      setFigmaToken(cachedData.figmaToken)
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

      toast.success('Comparison started successfully!')
      onComparisonStart(
        {
          jobId: response.data.job_id,
          status: response.data.status,
        },
        {
          figmaUrl,
          figmaToken,
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
      <div className="card">
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Start New Comparison
              </h2>
              <p className="text-gray-600">
                Enter your Figma design and website URL to begin the UI comparison
              </p>
            </div>
            {onShowHistory && (
              <button
                type="button"
                onClick={onShowHistory}
                className="btn-secondary flex items-center gap-2"
              >
                <Clock className="w-4 h-4" />
                History
              </button>
            )}
          </div>
          {cachedData && (
            <div className="mt-3 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700">
              ℹ️ Previous inputs restored
            </div>
          )}
        </div>

        {/* OAuth Section */}
        <div className="mb-6">
          <FigmaOAuth onTokenChange={setHasOAuthToken} />
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Figma Input */}
          <div>
            <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
              <Figma className="w-5 h-5 text-primary-600" />
              Figma Design
            </label>
            <input
              type="url"
              value={figmaUrl}
              onChange={(e) => setFigmaUrl(e.target.value)}
              placeholder="https://www.figma.com/file/..."
              className="input-field mb-3"
              required
            />
            
            {/* Token input - show toggle if OAuth is available */}
            {hasOAuthToken ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="useOAuth"
                    checked={useOAuth}
                    onChange={(e) => setUseOAuth(e.target.checked)}
                    className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                  />
                  <label htmlFor="useOAuth" className="text-sm text-gray-700">
                    Use OAuth token (recommended - higher rate limits)
                  </label>
                </div>
                {!useOAuth && (
                  <input
                    type="text"
                    value={figmaToken}
                    onChange={(e) => setFigmaToken(e.target.value)}
                    placeholder="Figma API Token (personal token)"
                    className="input-field"
                    required
                  />
                )}
              </div>
            ) : (
              <>
                <input
                  type="text"
                  value={figmaToken}
                  onChange={(e) => setFigmaToken(e.target.value)}
                  placeholder="Figma API Token (get from figma.com/developers)"
                  className="input-field"
                  required
                />
                <p className="text-xs text-gray-500 mt-2">
                  💡 Get your API token from{' '}
                  <a
                    href="https://www.figma.com/developers/api#access-tokens"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-600 hover:underline"
                  >
                    Figma Developers
                  </a>
                  {' '}or connect with OAuth above for higher rate limits.
                </p>
              </>
            )}
          </div>

          {/* Website Input */}
          <div>
            <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
              <Globe className="w-5 h-5 text-green-600" />
              Website URL
            </label>
            <input
              type="url"
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
              placeholder="https://example.com"
              className="input-field"
              required
            />
          </div>

          {/* Advanced Settings */}
          <div>
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-primary-600 transition-colors"
            >
              <Settings className="w-5 h-5" />
              Advanced Settings
              <span className="text-xs text-gray-500">
                ({showAdvanced ? 'hide' : 'show'})
              </span>
            </button>

            {showAdvanced && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-1 block">
                      Viewport Width
                    </label>
                    <input
                      type="number"
                      value={viewportWidth}
                      onChange={(e) => setViewportWidth(e.target.value)}
                      className="input-field"
                      min="320"
                      max="3840"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-1 block">
                      Viewport Height
                    </label>
                    <input
                      type="number"
                      value={viewportHeight}
                      onChange={(e) => setViewportHeight(e.target.value)}
                      className="input-field"
                      min="240"
                      max="2160"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    Comparison Mode
                  </label>
                  <select
                    value={comparisonMode}
                    onChange={(e) => setComparisonMode(e.target.value)}
                    className="input-field"
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
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                Start Comparison
              </>
            )}
          </button>
        </form>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <h3 className="font-semibold text-gray-900 mb-1">🎨 Colors</h3>
          <p className="text-sm text-gray-600">
            Detects color inconsistencies and brand guideline violations
          </p>
        </div>
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <h3 className="font-semibold text-gray-900 mb-1">📏 Spacing & Layout</h3>
          <p className="text-sm text-gray-600">
            Identifies spacing, alignment, and dimension differences
          </p>
        </div>
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <h3 className="font-semibold text-gray-900 mb-1">🔤 Typography</h3>
          <p className="text-sm text-gray-600">
            Compares fonts, sizes, weights, and text properties
          </p>
        </div>
      </div>
    </div>
  )
}
