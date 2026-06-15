import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { fetchMe } from '../api/client'
import { getToken } from '../api/auth'

export function getCreateCollectionPath(user) {
  if (user?.role === 'author') return '/author/create'
  if (getToken()) return '/author/create'
  return '/register?role=author'
}

export function useCurrentUser() {
  const location = useLocation()
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(() => {
    if (!getToken()) {
      setUser(null)
      setLoading(false)
      return
    }
    setLoading(true)
    fetchMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser, location.pathname])

  useEffect(() => {
    window.addEventListener('auth-changed', loadUser)
    return () => window.removeEventListener('auth-changed', loadUser)
  }, [loadUser])

  return { user, loading, refreshUser: loadUser }
}
