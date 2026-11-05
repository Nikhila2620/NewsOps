'use client'
import { useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { demoLogin, fetchMe } from '@/api/queries'
import { setToken, ApiError } from '@/api/client'

export interface Persona {
  user_id: string
  chat_handle: string
  display_name: string
  approver_rooms: string[]
  token: string
}

export function usePersona() {
  const qc = useQueryClient()
  const [persona, setPersona] = useState<Persona | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)

  const login = useCallback(async (name: 'alice' | 'sam') => {
    setLoading(true)
    setError(null)
    try {
      const result = await demoLogin(name)
      setToken(result.token)
      setPersona(result as Persona)
      // Refetch all queries with the new identity
      await qc.invalidateQueries()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }, [qc])

  return { persona, login, loading, error }
}
