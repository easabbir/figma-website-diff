import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'

interface User {
  id: string
  email: string
  full_name?: string
  is_active: boolean
  comparison_count: number
  profile_image?: string
  created_at?: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  requestSignupOTP: (email: string, password: string, fullName?: string) => Promise<{ expiresInMinutes: number }>
  verifySignupOTP: (email: string, otp: string) => Promise<void>
  resendOTP: (email: string) => Promise<{ expiresInMinutes: number }>
  logout: () => void
  updateProfile: (fullName?: string, profileImage?: string) => Promise<void>
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>
  refreshUser: () => Promise<void>
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const TOKEN_KEY = 'auth_token'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Load token from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY)
    if (storedToken) {
      setToken(storedToken)
      // Set default auth header
      axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
      // Fetch user info
      fetchUser(storedToken)
    } else {
      setIsLoading(false)
    }
  }, [])

  const fetchUser = async (authToken: string) => {
    try {
      const response = await axios.get('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${authToken}` }
      })
      setUser(response.data)
    } catch (error) {
      // Token is invalid, clear it
      localStorage.removeItem(TOKEN_KEY)
      setToken(null)
      delete axios.defaults.headers.common['Authorization']
    } finally {
      setIsLoading(false)
    }
  }

  const login = async (email: string, password: string) => {
    const response = await axios.post('/api/v1/auth/login', { email, password })
    const { access_token } = response.data
    
    // Store token
    localStorage.setItem(TOKEN_KEY, access_token)
    setToken(access_token)
    
    // Set default auth header
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
    
    // Fetch user info
    await fetchUser(access_token)
  }

  const requestSignupOTP = async (email: string, password: string, fullName?: string): Promise<{ expiresInMinutes: number }> => {
    const response = await axios.post('/api/v1/auth/signup/request-otp', {
      email,
      password,
      full_name: fullName
    })
    return { expiresInMinutes: response.data.expires_in_minutes || 10 }
  }

  const verifySignupOTP = async (email: string, otp: string): Promise<void> => {
    const response = await axios.post('/api/v1/auth/signup/verify-otp', {
      email,
      otp
    })
    const { access_token } = response.data
    
    // Store token
    localStorage.setItem(TOKEN_KEY, access_token)
    setToken(access_token)
    
    // Set default auth header
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
    
    // Fetch user info
    await fetchUser(access_token)
  }

  const resendOTP = async (email: string): Promise<{ expiresInMinutes: number }> => {
    const response = await axios.post('/api/v1/auth/signup/resend-otp', { email })
    return { expiresInMinutes: response.data.expires_in_minutes || 10 }
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
    delete axios.defaults.headers.common['Authorization']
  }

  const updateProfile = async (fullName?: string, profileImage?: string) => {
    const response = await axios.put('/api/v1/auth/profile', {
      full_name: fullName,
      profile_image: profileImage
    })
    setUser(response.data)
  }

  const changePassword = async (currentPassword: string, newPassword: string) => {
    await axios.put('/api/v1/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    })
  }

  const refreshUser = async () => {
    if (token) {
      await fetchUser(token)
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        requestSignupOTP,
        verifySignupOTP,
        resendOTP,
        logout,
        updateProfile,
        changePassword,
        refreshUser,
        isAuthenticated: !!user
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
