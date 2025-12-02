import { useState } from 'react'
import { Mail, Lock, User, Loader2, CheckCircle, ArrowRight, Eye, EyeOff, Sparkles, Zap, Shield, BarChart3 } from 'lucide-react'
import { toast } from 'react-toastify'
import { useAuth } from '../context/AuthContext'

type AuthTab = 'login' | 'signup'

export default function AuthPage() {
  const [activeTab, setActiveTab] = useState<AuthTab>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const { login, signup } = useAuth()

  const resetForm = () => {
    setEmail('')
    setPassword('')
    setFullName('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      if (activeTab === 'login') {
        await login(email, password)
        toast.success('Welcome back!')
      } else {
        await signup(email, password, fullName || undefined)
        toast.success('Account created successfully!')
      }
      resetForm()
    } catch (error: any) {
      const message = error.response?.data?.detail || 'An error occurred'
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  const switchTab = (tab: AuthTab) => {
    setActiveTab(tab)
    resetForm()
  }

  const features = [
    { icon: Zap, title: 'Instant Comparison', desc: 'Compare designs in seconds' },
    { icon: Shield, title: 'Pixel Perfect', desc: 'Catch every visual difference' },
    { icon: BarChart3, title: 'Detailed Reports', desc: 'Get actionable insights' },
    { icon: Sparkles, title: 'Smart Detection', desc: 'Intelligent detection backed by thoughtful analysis' },
  ]

  return (
    <div className="min-h-screen flex">
      {/* Left Side - Branding & Features */}
      <div className="hidden lg:flex lg:w-[55%] relative overflow-hidden">
        {/* Animated Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-violet-600 via-purple-600 to-indigo-700" />
        <div className="absolute inset-0 opacity-30" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.1'%3E%3Ccircle cx='30' cy='30' r='2'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")" }} />
        
        {/* Floating Orbs */}
        <div className="absolute top-20 left-20 w-72 h-72 bg-white/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-20 right-20 w-96 h-96 bg-pink-500/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute top-1/2 left-1/3 w-64 h-64 bg-cyan-400/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }} />
        
        <div className="relative z-10 p-12 flex flex-col justify-between w-full">
          <div>
            {/* Logo */}
            <div className="flex items-center gap-4 mb-16">
              <div className="relative">
                <div className="absolute inset-0 bg-white/20 rounded-2xl blur-xl" />
                <div className="relative p-4 bg-white/10 backdrop-blur-sm rounded-2xl border border-white/20">
                  <svg className="w-10 h-10 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                  </svg>
                </div>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white tracking-tight">UI Diff Checker</h1>
                <p className="text-white/60 text-sm font-medium">Figma ↔ Website Comparison</p>
              </div>
            </div>

            {/* Hero Text */}
            <div className="space-y-6 max-w-lg">
              <h2 className="text-5xl font-bold text-white leading-[1.1] tracking-tight">
                Pixel-perfect
                <span className="block text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-pink-300">
                  design validation
                </span>
              </h2>
              <p className="text-white/70 text-lg leading-relaxed">
                Bridge the gap between design and development. Catch visual inconsistencies before they reach production.
              </p>
            </div>

            {/* Feature Cards */}
            <div className="grid grid-cols-2 gap-4 mt-12">
              {features.map((feature, index) => (
                <div 
                  key={index} 
                  className="group p-4 bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all duration-300"
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-white/10 rounded-xl group-hover:bg-white/20 transition-colors">
                      <feature.icon className="w-5 h-5 text-cyan-300" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white text-sm">{feature.title}</h3>
                      <p className="text-white/50 text-xs mt-0.5">{feature.desc}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between">
            <p className="text-white/40 text-sm">© 2025 UI Diff Checker</p>
            <div className="flex items-center gap-2">
              <div className="flex -space-x-2">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="w-8 h-8 rounded-full bg-gradient-to-br from-white/20 to-white/5 border-2 border-purple-600 flex items-center justify-center">
                    <span className="text-xs text-white/60">👤</span>
                  </div>
                ))}
              </div>
              <span className="text-white/50 text-sm ml-2">500+ designers trust us</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right Side - Auth Form */}
      <div className="w-full lg:w-[45%] flex items-center justify-center p-4 sm:p-6 bg-gradient-to-b from-gray-50 to-white overflow-y-auto">
        <div className="w-full max-w-[400px] my-auto">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-6 justify-center">
            <div className="p-2.5 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl shadow-lg shadow-purple-500/25">
              <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
            </div>
            <h1 className="text-lg font-bold text-gray-900">UI Diff Checker</h1>
          </div>

          {/* Form Card */}
          <div className="bg-white rounded-2xl shadow-xl shadow-gray-200/50 p-6 border border-gray-100">
            {/* Header */}
            <div className="text-center mb-5">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl shadow-lg shadow-purple-500/30 mb-3">
                {activeTab === 'login' ? (
                  <ArrowRight className="w-5 h-5 text-white" />
                ) : (
                  <Sparkles className="w-5 h-5 text-white" />
                )}
              </div>
              <h2 className="text-xl font-bold text-gray-900">
                {activeTab === 'login' ? 'Welcome back!' : 'Get started'}
              </h2>
              <p className="text-gray-500 mt-1 text-sm">
                {activeTab === 'login'
                  ? 'Enter your credentials to continue'
                  : 'Create your account in seconds'}
              </p>
            </div>

            {/* Tabs */}
            <div className="flex bg-gray-100/80 rounded-xl p-1 mb-5">
              <button
                onClick={() => switchTab('login')}
                className={`flex-1 py-2.5 text-sm font-semibold rounded-lg transition-all duration-300 ${
                  activeTab === 'login'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Sign In
              </button>
              <button
                onClick={() => switchTab('signup')}
                className={`flex-1 py-2.5 text-sm font-semibold rounded-lg transition-all duration-300 ${
                  activeTab === 'signup'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Sign Up
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-3">
              {activeTab === 'signup' && (
                <div className="space-y-1">
                  <label className="block text-sm font-medium text-gray-700">
                    Full Name
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="John Doe"
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:bg-white focus:border-violet-500 focus:ring-1 focus:ring-violet-500 transition-all text-gray-900 placeholder:text-gray-400 text-sm"
                    />
                  </div>
                </div>
              )}

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

              <div className="space-y-1">
                <label className="block text-sm font-medium text-gray-700">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    minLength={6}
                    className="w-full pl-10 pr-10 py-2.5 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:bg-white focus:border-violet-500 focus:ring-1 focus:ring-violet-500 transition-all text-gray-900 placeholder:text-gray-400 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {activeTab === 'signup' && (
                  <p className="text-xs text-gray-400 flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" /> Minimum 6 characters
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white font-semibold rounded-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 group shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40 mt-4"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm">{activeTab === 'login' ? 'Signing in...' : 'Creating account...'}</span>
                  </>
                ) : (
                  <>
                    <span className="text-sm">{activeTab === 'login' ? 'Sign In' : 'Create Account'}</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </>
                )}
              </button>
            </form>

            {/* Footer */}
            <p className="text-center text-sm text-gray-500 mt-4">
              {activeTab === 'login' ? (
                <>
                  New here?{' '}
                  <button
                    type="button"
                    onClick={() => switchTab('signup')}
                    className="text-violet-600 hover:text-violet-700 font-semibold"
                  >
                    Create an account
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => switchTab('login')}
                    className="text-violet-600 hover:text-violet-700 font-semibold"
                  >
                    Sign in
                  </button>
                </>
              )}
            </p>
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
    </div>
  )
}
