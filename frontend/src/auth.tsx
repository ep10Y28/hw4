import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { User } from './api.ts'
import * as api from './api.ts'

type AuthState = {
  user: User | null
  ready: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (data: { first_name: string; last_name: string; email: string; password: string }) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  // On page load, ask the backend who the saved session belongs to.
  useEffect(() => {
    api.fetchMe().then((u) => {
      setUser(u)
      setReady(true)
    })
  }, [])

  const value: AuthState = {
    user,
    ready,
    login: async (email, password) => setUser(await api.login(email, password)),
    signup: async (data) => setUser(await api.signup(data)),
    logout: async () => {
      await api.logout()
      setUser(null)
    },
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
