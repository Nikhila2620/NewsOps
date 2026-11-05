'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState, type ReactNode } from 'react'
import { useTheme } from '@/hooks/useTheme'
import { usePersona } from '@/hooks/usePersona'
import dynamic from 'next/dynamic'
import { api } from '@/api/client'
import { pushToast } from './Toast'

const RoomPanel = dynamic(() => import('@/features/room/RoomPanel'), { ssr: false })

const ROOMS = [
  { key: 'aiml',     label: '#aiml' },
  { key: 'cloud',    label: '#cloud' },
  { key: 'security', label: '#security' },
]

const NAV = [
  { href: '/',            label: 'Inbox' },
  { href: '/radar',       label: 'Tech Radar' },
  { href: '/dependencies',label: 'Dependencies' },
  { href: '/review',      label: 'Review' },
]

export default function Shell({ children }: { children: ReactNode }) {
  const [theme, toggleTheme] = useTheme()
  const { persona, login, loading } = usePersona()
  const pathname = usePathname()
  const [activeRoom, setActiveRoom] = useState('aiml')
  const [roomOpen,   setRoomOpen]   = useState(false)

  const handleReset = async () => {
    try {
      await api.post('/demo/reset')
      pushToast({ kind: 'success', message: 'Demo reset — ready for a new run.' })
    } catch {
      pushToast({ kind: 'error', message: 'Reset failed. Is the backend running?' })
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100dvh',
                  background: 'var(--bg)' }}>
      {/* ── Header ── */}
      <header style={{
        display: 'flex', alignItems: 'center', gap: 16,
        padding: '0 24px', height: 52,
        background: 'var(--surface)', borderBottom: '1px solid var(--line)',
        position: 'sticky', top: 0, zIndex: 100,
      }}>
        {/* Brand */}
        <Link href="/" style={{ textDecoration: 'none', color: 'var(--ink)',
                                 fontFamily: 'Bricolage Grotesque, sans-serif',
                                 fontWeight: 800, fontSize: 18, letterSpacing: '-0.5px' }}>
          NewsOps
        </Link>
        <span style={{ color: 'var(--line)', fontSize: 18 }}>|</span>

        {/* Ticker placeholder */}
        <div style={{ flex: 1, overflow: 'hidden', color: 'var(--mute)', fontSize: 12 }}>
          <span>Latest: AI models, cloud security, dependency updates…</span>
        </div>

        {/* Persona switch */}
        <div style={{ display: 'flex', gap: 4 }}>
          {(['alice', 'sam'] as const).map(name => (
            <button key={name}
                    onClick={() => login(name)}
                    disabled={loading}
                    aria-pressed={persona?.display_name.toLowerCase().startsWith(name)}
                    style={{
                      padding: '4px 10px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
                      border: '1px solid var(--line)',
                      background: persona?.display_name.toLowerCase().startsWith(name)
                        ? 'var(--accent)' : 'var(--surface2)',
                      color: persona?.display_name.toLowerCase().startsWith(name)
                        ? '#fff' : 'var(--ink)',
                      fontWeight: 600,
                    }}>
              {name.charAt(0).toUpperCase() + name.slice(1)}
            </button>
          ))}
        </div>

        {/* Room panel toggle (mobile) */}
        <button onClick={() => setRoomOpen(v => !v)}
                aria-label="Open room panel"
                style={{ display: 'none', background: 'none', border: 'none',
                         color: 'var(--ink)', cursor: 'pointer', fontSize: 18 }}
                className="room-toggle">
          💬
        </button>

        {/* Theme toggle */}
        <button onClick={toggleTheme}
                aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
                style={{ background: 'none', border: 'none', cursor: 'pointer',
                         color: 'var(--ink)', fontSize: 16 }}>
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </header>

      <div style={{ display: 'flex', flex: 1 }}>
        {/* ── Left rail ── */}
        <nav aria-label="Main navigation"
             style={{
               width: 200, flexShrink: 0,
               background: 'var(--surface)', borderRight: '1px solid var(--line)',
               padding: '16px 0', display: 'flex', flexDirection: 'column', gap: 4,
             }}>
          {NAV.map(item => (
            <Link key={item.href} href={item.href}
                  style={{
                    padding: '8px 20px', textDecoration: 'none', fontSize: 14,
                    color: pathname === item.href ? 'var(--accent)' : 'var(--ink)',
                    background: pathname === item.href ? 'var(--surface2)' : 'transparent',
                    borderRight: pathname === item.href ? '2px solid var(--accent)' : '2px solid transparent',
                    fontWeight: pathname === item.href ? 600 : 400,
                    display: 'block',
                  }}>
              {item.label}
            </Link>
          ))}

          {/* Room selector */}
          <div style={{ padding: '16px 20px 4px', fontSize: 11, color: 'var(--mute)',
                        fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
            Rooms
          </div>
          {ROOMS.map(r => (
            <button key={r.key}
                    onClick={() => setActiveRoom(r.key)}
                    style={{
                      padding: '6px 20px', textAlign: 'left', border: 'none', cursor: 'pointer',
                      fontSize: 13, background: activeRoom === r.key ? 'var(--surface2)' : 'transparent',
                      color: activeRoom === r.key ? 'var(--ink)' : 'var(--mute)',
                      fontWeight: activeRoom === r.key ? 600 : 400,
                    }}>
              {r.label}
            </button>
          ))}

          <div style={{ flex: 1 }} />

          {/* Reset demo */}
          <button onClick={handleReset}
                  style={{
                    margin: '0 20px 16px', padding: '6px 12px', fontSize: 12,
                    background: 'var(--surface2)', color: 'var(--mute)',
                    border: '1px solid var(--line)', borderRadius: 6, cursor: 'pointer',
                  }}>
            ↺ Reset demo
          </button>

          {/* Persona info */}
          {persona && (
            <div style={{ margin: '0 20px 12px', padding: '8px 10px', fontSize: 11,
                          background: 'var(--surface2)', borderRadius: 6, color: 'var(--mute)' }}>
              <strong style={{ color: 'var(--ink)' }}>{persona.display_name}</strong>
              <div>Approves: {persona.approver_rooms.join(', ') || 'none'}</div>
            </div>
          )}
        </nav>

        {/* ── Main content ── */}
        <main style={{ flex: 1, overflow: 'auto', minWidth: 0 }}>
          {children}
        </main>

        {/* ── Room panel (always visible ≥1180px, slide-over below) ── */}
        <aside style={{ width: 300, flexShrink: 0, borderLeft: '1px solid var(--line)' }}
               className="room-panel-desktop">
          <RoomPanel roomKey={activeRoom} />
        </aside>

        {/* Slide-over for mobile */}
        {roomOpen && (
          <div style={{ position: 'fixed', inset: 0, zIndex: 200 }}>
            <div onClick={() => setRoomOpen(false)}
                 style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.4)' }} />
            <aside style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 320 }}>
              <RoomPanel roomKey={activeRoom} onClose={() => setRoomOpen(false)} slideOver />
            </aside>
          </div>
        )}
      </div>

      <style>{`
        @media (max-width: 1180px) { .room-panel-desktop { display: none !important; } .room-toggle { display: flex !important; } }
        @media (max-width: 820px)  {
          nav[aria-label="Main navigation"] {
            width: 100% !important;
            flex-direction: row !important;
            overflow-x: auto !important;
            border-right: none !important;
            border-bottom: 1px solid var(--line) !important;
            padding: 0 !important;
            gap: 0 !important;
          }
          div[style*="display: flex"][style*="flex: 1"] { flex-direction: column !important; }
        }
        @media (max-width: 400px) { body { overflow-x: hidden !important; } }
      `}</style>
    </div>
  )
}
