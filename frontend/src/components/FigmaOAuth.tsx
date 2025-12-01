import { useState, useEffect } from 'react'
import { LogIn, LogOut, CheckCircle, AlertCircle, Loader2, ExternalLink } from 'lucide-react'
import axios from 'axios'
import { toast } from 'react-toastify'

interface OAuthStatus {
  configured: boolean
  authenticated: boolean
  user_id?: string
  message: string
}

interface FigmaOAuthProps {
  onTokenChange?: (hasToken: boolean) => void
}

export default function FigmaOAuth({ onTokenChange }: FigmaOAuthProps) {
  const [status, setStatus] = useState<OAuthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [connecting, setConnecting] = useState(false)

  useEffect(() => {
    checkOAuthStatus()
    
    // Check for OAuth callback result in URL
    const params = new URLSearchParams(window.location.search)
    const oauthResult = params.get('oauth')
    
    if (oauthResult === 'success') {
      toast.success('Successfully connected to Figma!')
      // Clean up URL
      window.history.replaceState({}, '', window.location.pathname)
      checkOAuthStatus()
    } else if (oauthResult === 'error') {
      const message = params.get('message') || 'OAuth failed'
      toast.error(`Figma connection failed: ${message}`)
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  const checkOAuthStatus = async () => {
    try {
      const response = await axios.get('/api/v1/oauth/status')
      setStatus(response.data)
      onTokenChange?.(response.data.authenticated)
    } catch (err) {
      console.error('Failed to check OAuth status:', err)
      setStatus({
        configured: false,
        authenticated: false,
        message: 'Failed to check OAuth status'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleConnect = async () => {
    setConnecting(true)
    try {
      const response = await axios.get('/api/v1/oauth/authorize')
      // Redirect to Figma OAuth
      window.location.href = response.data.authorization_url
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to start OAuth flow')
      setConnecting(false)
    }
  }

  const handleDisconnect = async () => {
    try {
      await axios.delete('/api/v1/oauth/logout')
      toast.success('Disconnected from Figma')
      setStatus({
        configured: true,
        authenticated: false,
        message: 'Logged out'
      })
      onTokenChange?.(false)
    } catch (err) {
      toast.error('Failed to disconnect')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="text-sm">Checking Figma connection...</span>
      </div>
    )
  }

  if (!status?.configured) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
          <div>
            <h4 className="font-medium text-yellow-800">OAuth Not Configured</h4>
            <p className="text-sm text-yellow-700 mt-1">
              To use OAuth (recommended for higher rate limits), set these environment variables:
            </p>
            <ul className="text-sm text-yellow-700 mt-2 list-disc list-inside">
              <li><code className="bg-yellow-100 px-1 rounded">FIGMA_CLIENT_ID</code></li>
              <li><code className="bg-yellow-100 px-1 rounded">FIGMA_CLIENT_SECRET</code></li>
            </ul>
            <a 
              href="https://www.figma.com/developers/apps" 
              target="_blank" 
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm text-yellow-800 hover:text-yellow-900 mt-2 underline"
            >
              Create OAuth App on Figma
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>
    )
  }

  if (status.authenticated) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <div>
              <h4 className="font-medium text-green-800">Connected to Figma</h4>
              <p className="text-sm text-green-700">
                Using OAuth token (higher rate limits)
                {status.user_id && <span className="ml-1">• User: {status.user_id}</span>}
              </p>
            </div>
          </div>
          <button
            onClick={handleDisconnect}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Disconnect
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-blue-600" />
          <div>
            <h4 className="font-medium text-blue-800">Connect with Figma OAuth</h4>
            <p className="text-sm text-blue-700">
              Get higher rate limits by connecting with OAuth instead of personal token
            </p>
          </div>
        </div>
        <button
          onClick={handleConnect}
          disabled={connecting}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {connecting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <LogIn className="w-4 h-4" />
          )}
          Connect Figma
        </button>
      </div>
    </div>
  )
}
