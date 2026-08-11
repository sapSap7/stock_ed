import { useCallback, useEffect, useState } from 'react'
import { loginWithGoogle, setAuthToken } from '../api'

const STORAGE_KEY = 'auth'

export function useAuth() {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      try {
        const { token, user: storedUser } = JSON.parse(stored)
        setAuthToken(token)
        setUser(storedUser)
      } catch {
        localStorage.removeItem(STORAGE_KEY)
      }
    }
    setReady(true)
  }, [])

  const login = useCallback(async (credential) => {
    const { token, user: loggedInUser } = await loginWithGoogle(credential)
    setAuthToken(token)
    setUser(loggedInUser)
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ token, user: loggedInUser }))
  }, [])

  const logout = useCallback(() => {
    setAuthToken(null)
    setUser(null)
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  return { user, ready, login, logout }
}
