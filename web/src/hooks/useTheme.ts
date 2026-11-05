'use client'
import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>('light')

  useEffect(() => {
    try {
      const stored = localStorage.getItem('newsops_theme') as Theme | null
      const preferred = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
      const initial = stored ?? preferred
      setTheme(initial)
      document.documentElement.setAttribute('data-theme', initial)
    } catch {}
  }, [])

  const toggle = () => {
    setTheme(prev => {
      const next = prev === 'dark' ? 'light' : 'dark'
      document.documentElement.setAttribute('data-theme', next)
      try { localStorage.setItem('newsops_theme', next) } catch {}
      return next
    })
  }

  return [theme, toggle]
}
