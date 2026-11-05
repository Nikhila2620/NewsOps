'use client'

import { useEffect, useState } from 'react'

export interface ToastItem {
  id: string
  message: string
  kind: 'info' | 'error' | 'success'
}

// Simple event bus for toasts
const listeners: Array<(t: ToastItem) => void> = []
export function pushToast(t: Omit<ToastItem, 'id'>) {
  const item = { ...t, id: `toast-${Date.now()}` }
  listeners.forEach(l => l(item))
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  useEffect(() => {
    const handler = (t: ToastItem) => {
      setToasts(prev => [...prev, t])
      setTimeout(() => setToasts(prev => prev.filter(x => x.id !== t.id)), 4000)
    }
    listeners.push(handler)
    return () => { const i = listeners.indexOf(handler); if (i > -1) listeners.splice(i, 1) }
  }, [])

  const COLORS = { error: 'var(--bad-bg)', success: 'var(--good-bg)', info: 'var(--surface2)' }
  const TEXT   = { error: 'var(--bad-fg)', success: 'var(--good-fg)', info: 'var(--ink)' }

  return (
    <div role="status" aria-live="polite"
         style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
                  display: 'flex', flexDirection: 'column', gap: 8 }}>
      {toasts.map(t => (
        <div key={t.id}
             style={{
               background: COLORS[t.kind], color: TEXT[t.kind],
               padding: '10px 18px', borderRadius: 10, fontSize: 13,
               boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
               maxWidth: 340, lineHeight: 1.4,
             }}>
          {t.message}
        </div>
      ))}
    </div>
  )
}
