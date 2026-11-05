'use client'
/**
 * Starts MSW browser worker when NEXT_PUBLIC_MOCK=1.
 * Rendered once at the top of the app tree so mocks are ready before any fetch.
 */
import { useEffect, useState, type ReactNode } from 'react'

export function MockProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(process.env.NEXT_PUBLIC_MOCK !== '1')

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_MOCK !== '1') return
    import('./browser').then(({ worker }) =>
      worker.start({ quiet: true } as Parameters<typeof worker.start>[0]).then(() => setReady(true))
    )
  }, [])

  if (!ready) return null
  return <>{children}</>
}
