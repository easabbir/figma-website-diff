import { useState } from 'react'
import { Mail, Loader2, ArrowLeft, CheckCircle, Shield, KeyRound } from 'lucide-react'
import { toast } from 'react-toastify'
import axios from 'axios'

interface ForgotPasswordPageProps {
  onBack: () => void
}

export default function ForgotPasswordPage({ onBack }: ForgotPasswordPageProps) {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      await axios.post('/api/v1/auth/forgot-password', { email })
      setIsSubmitted(true)
      toast.success('Password reset instructions sent!')
    } catch (error: any) {
      // Always show success for security (don't reveal if email exists)
      setIsSubmitted(true)
      toast.success('If an account exists, you will receive reset instructions.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-b from-gray-50 to-white">
      <div className="w-full max-w-[400px]">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-6 justify-center">
          <div className="p-2.5 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl shadow-lg shadow-purple-500/25">
            <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1 className="text-lg font-bold text-gray-900">Pixel Perfect UI</h1>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-xl shadow-gray-200/50 p-6 border border-gray-100">
          {isSubmitted ? (
            // Success State
            <>
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl shadow-lg shadow-green-500/30 mb-4">
                  <CheckCircle className="w-6 h-6 text-white" />
                </div>
                <h2 className="text-xl font-bold text-gray-900">Check your email</h2>
                <p className="text-gray-500 mt-2 text-sm">
                  If an account exists for <span className="text-violet-600 font-medium">{email}</span>, 
                  you will receive a password reset link shortly.
                </p>
              </div>

              <div className="mt-6 p-4 bg-violet-50 rounded-xl border border-violet-100">
                <p className="text-sm text-violet-700">
                  <strong>Didn't receive the email?</strong>
                </p>
                <ul className="text-sm text-violet-600 mt-2 space-y-1">
                  <li>• Check your spam folder</li>
                  <li>• Make sure you entered the correct email</li>
                  <li>• Wait a few minutes and try again</li>
                </ul>
              </div>

              <button
                onClick={onBack}
                className="w-full mt-6 py-3 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white font-semibold rounded-lg transition-all duration-300 flex items-center justify-center gap-2 shadow-lg shadow-purple-500/25"
              >
                <ArrowLeft className="w-4 h-4" />
                <span className="text-sm">Back to Login</span>
              </button>
            </>
          ) : (
            // Form State
            <>
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-14 h-14 bg-gradient-to-br from-violet-500 to-purple-600 rounded-2xl shadow-lg shadow-purple-500/30 mb-4">
                  <KeyRound className="w-6 h-6 text-white" />
                </div>
                <h2 className="text-xl font-bold text-gray-900">Forgot password?</h2>
                <p className="text-gray-500 mt-2 text-sm">
                  No worries! Enter your email and we'll send you reset instructions.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1">
                  <label className="block text-sm font-medium text-gray-700">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      required
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:bg-white focus:border-violet-500 focus:ring-1 focus:ring-violet-500 transition-all text-gray-900 placeholder:text-gray-400 text-sm"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoading || !email}
                  className="w-full py-3 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white font-semibold rounded-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm">Sending...</span>
                    </>
                  ) : (
                    <>
                      <Mail className="w-4 h-4" />
                      <span className="text-sm">Send Reset Link</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={onBack}
                  className="w-full py-2.5 text-gray-600 hover:text-gray-900 font-medium text-sm flex items-center justify-center gap-1 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Back to Login
                </button>
              </form>
            </>
          )}
        </div>

        {/* Trust Badge */}
        <div className="mt-4 text-center">
          <p className="text-xs text-gray-400 flex items-center justify-center gap-1.5">
            <Shield className="w-3.5 h-3.5" />
            Your data is secure and encrypted
          </p>
        </div>
      </div>
    </div>
  )
}
