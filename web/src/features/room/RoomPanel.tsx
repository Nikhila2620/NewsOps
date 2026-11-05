'use client'

import { useRef, useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useRoomStream } from './useRoomStream'
import { keys, fetchSwitchStatus, fetchHealthz } from '@/api/queries'

interface Props {
  roomKey: string
  onClose?: () => void
  slideOver?: boolean
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function formatMessage(text: string): string {
  // Escape first, then apply safe markdown: **bold** and `code`
  const escaped = escapeHtml(text)
  return escaped
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/@(\w+)/g, '<span class="mention">@$1</span>')
}

const CONNECTION_LABELS: Record<string, string> = {
  live:         'LIVE',
  reconnecting: 'RECONNECTING',
  polling:      'POLLING',
  offline:      'OFFLINE',
}

const CONNECTION_COLORS: Record<string, string> = {
  live:         '#0d7f57',
  reconnecting: '#8f5b00',
  polling:      '#8f5b00',
  offline:      '#c0263a',
}

const QUICK_CHIPS = (room: string) => [
  { label: `@scout ${room} last 24h`, text: `@scout ${room} last 24h` },
  { label: '@editor approve',         text: '@editor approve' },
  { label: '@editor publish',         text: '@editor publish' },
]

export default function RoomPanel({ roomKey, onClose, slideOver }: Props) {
  const { messages, step, connection, send } = useRoomStream(roomKey)
  const [input, setInput] = useState('')
  const listRef = useRef<HTMLDivElement>(null)

  const { data: switchStatus } = useQuery({
    queryKey: keys.switchStatus(),
    queryFn:  fetchSwitchStatus,
    staleTime: 60_000,
  })
  const { data: health } = useQuery({
    queryKey: keys.healthz(),
    queryFn:  fetchHealthz,
    staleTime: 30_000,
  })

  // Auto-scroll to bottom
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text) return
    setInput('')
    await send(text)
  }

  const isMock = (health as { is_mock?: boolean } | undefined)?.is_mock
  const switchConnected = switchStatus?.connected

  const wrapClass = slideOver
    ? 'fixed inset-y-0 right-0 z-50 w-80 flex flex-col shadow-2xl'
    : 'flex flex-col h-full'

  return (
    <div
      className={wrapClass}
      style={{ background: 'var(--surface)', borderLeft: '1px solid var(--line)' }}
    >
      {/* ── Header ── */}
      <div style={{ borderBottom: '1px solid var(--line)', padding: '12px 16px' }}
           className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: 14 }}>
            #{roomKey}
          </span>
          {isMock && (
            <span style={{ background: 'var(--warn-bg)', color: 'var(--warn-fg)',
                           fontSize: 11, padding: '1px 6px', borderRadius: 4 }}>
              Demo DB
            </span>
          )}
          {/* Connection dot */}
          <span className="flex items-center gap-1" style={{ fontSize: 11, color: 'var(--mute)' }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%', display: 'inline-block',
              background: CONNECTION_COLORS[connection],
            }} />
            {CONNECTION_LABELS[connection]}
          </span>
        </div>
        {onClose && (
          <button onClick={onClose}
                  aria-label="Close room panel"
                  style={{ color: 'var(--mute)', background: 'none', border: 'none',
                           cursor: 'pointer', fontSize: 18, lineHeight: 1 }}>
            ×
          </button>
        )}
      </div>

      {/* ── Honesty banner ── */}
      {!switchConnected && (
        <div style={{ background: 'var(--surface2)', padding: '6px 16px',
                      fontSize: 12, color: 'var(--mute)', borderBottom: '1px solid var(--line)' }}>
          Switch not connected — showing backend activity only
        </div>
      )}

      {/* ── Message list ── */}
      <div ref={listRef}
           role="log"
           aria-live="polite"
           aria-label={`${roomKey} room messages`}
           className="flex-1 overflow-y-auto"
           style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {messages.length === 0 && (
          <p style={{ color: 'var(--mute)', fontSize: 13, textAlign: 'center', marginTop: 32 }}>
            No messages yet. Send <code>@scout {roomKey} last 24h</code> to start.
          </p>
        )}
        {messages.map((m, i) => {
          const isAgent = ['scout', 'analyst', 'editor'].includes(m.who ?? '')
          const isBlocked = m.blocked
          const agentColor = m.who === 'scout' ? 'var(--scout)'
                           : m.who === 'analyst' ? 'var(--analyst)'
                           : m.who === 'editor'  ? 'var(--editor)'
                           : 'var(--mute)'
          return (
            <div key={m.seq > 0 ? m.seq : `local-${i}`}
                 style={{
                   opacity: m._state === 'sending' ? 0.6 : 1,
                   background: isBlocked ? 'var(--bad-bg)' : 'transparent',
                   borderRadius: isBlocked ? 8 : 0,
                   padding: isBlocked ? '6px 10px' : 0,
                 }}>
              {/* Handoff pill */}
              {m.handoff && (
                <div style={{
                  display: 'inline-block', background: 'var(--surface2)',
                  color: 'var(--mute)', fontSize: 11, padding: '2px 8px',
                  borderRadius: 12, marginBottom: 4,
                }}>
                  {m.handoff}
                </div>
              )}
              {/* Who */}
              {m.who && m.who !== 'me' && (
                <div style={{ fontSize: 11, color: isAgent ? agentColor : 'var(--mute)',
                              fontWeight: 600, marginBottom: 2 }}>
                  {m.who}{m.system ? ' · system' : ''}
                </div>
              )}
              {/* Text */}
              {m.text && (
                <div
                  style={{
                    fontSize: 13,
                    color: isBlocked ? 'var(--bad-fg)' : 'var(--ink)',
                    lineHeight: 1.5,
                  }}
                  // Safe: formatMessage escapes HTML before applying markup
                  dangerouslySetInnerHTML={{ __html: formatMessage(m.text) }}
                />
              )}
              {/* Failure state */}
              {m._state === 'failed' && (
                <div style={{ fontSize: 11, color: 'var(--bad-fg)', marginTop: 2 }}>
                  Failed to send.{' '}
                  <button style={{ color: 'var(--accent)', background: 'none', border: 'none',
                                   cursor: 'pointer', textDecoration: 'underline', fontSize: 11 }}>
                    Retry
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* ── Quick chips ── */}
      <div style={{ padding: '6px 16px', display: 'flex', gap: 6, flexWrap: 'wrap',
                    borderTop: '1px solid var(--line)' }}>
        {QUICK_CHIPS(roomKey).map(c => (
          <button key={c.label}
                  onClick={() => setInput(c.text)}
                  style={{
                    background: 'var(--surface2)', color: 'var(--mute)', border: 'none',
                    borderRadius: 20, padding: '3px 10px', fontSize: 11, cursor: 'pointer',
                  }}>
            {c.label}
          </button>
        ))}
      </div>

      {/* ── Input row ── */}
      <div style={{ padding: '10px 16px', borderTop: '1px solid var(--line)',
                    display: 'flex', gap: 8 }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
          placeholder={`Message #${roomKey}…`}
          aria-label={`Send message to #${roomKey}`}
          style={{
            flex: 1,
            background: 'var(--surface2)',
            border: '1px solid var(--line)',
            borderRadius: 8,
            color: 'var(--ink)',
            padding: '8px 12px',
            fontSize: 13,
            outline: 'none',
          }}
        />
        <button
          onClick={handleSend}
          aria-label="Send message"
          disabled={!input.trim()}
          style={{
            background: 'var(--accent)', color: '#fff', border: 'none',
            borderRadius: 8, padding: '0 14px', cursor: 'pointer',
            fontSize: 13, fontWeight: 600,
            opacity: input.trim() ? 1 : 0.5,
          }}>
          Send
        </button>
      </div>
    </div>
  )
}
