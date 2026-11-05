'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchAgentActivity, type AgentActivity } from '@/api/queries'

const ROOMS = [
  { key: '', label: 'All Rooms' },
  { key: 'aiml', label: '#aiml' },
  { key: 'cloud', label: '#cloud' },
  { key: 'security', label: '#security' },
]

export default function ActivityPage() {
  const [selectedRoom, setSelectedRoom] = useState('')

  const { data: activities, isLoading, error } = useQuery<AgentActivity[]>({
    queryKey: ['agentActivity', selectedRoom],
    queryFn: () => fetchAgentActivity(selectedRoom || undefined),
    refetchInterval: 5000, // Polls every 5s
  })

  return (
    <main style={{ padding: '24px 16px', maxWidth: 960, margin: '0 auto', width: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: 'var(--ink)' }}>
            Switch Agent Activity Feed
          </h1>
          <p style={{ fontSize: 13, color: 'var(--mute)', marginTop: 4 }}>
            Live coordination log of autonomous Scout, Analyst, and Editor actions (polls every 5s).
          </p>
        </div>

        {/* Room Filter */}
        <div style={{ display: 'flex', gap: 6 }}>
          {ROOMS.map(r => (
            <button
              key={r.key}
              onClick={() => setSelectedRoom(r.key)}
              style={{
                padding: '6px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
                border: '1px solid var(--line)',
                background: selectedRoom === r.key ? 'var(--accent)' : 'var(--surface)',
                color: selectedRoom === r.key ? '#fff' : 'var(--ink)',
                fontWeight: 600,
              }}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div style={{ padding: 24, background: 'var(--surface)', borderRadius: 8, color: 'var(--mute)', fontSize: 14 }}>
          Loading live agent activity...
        </div>
      )}

      {/* Error state */}
      {error && (
        <div style={{ padding: 24, background: 'var(--surface)', borderRadius: 8, color: 'var(--error)', fontSize: 14 }}>
          Could not load agent activities. Ensure the NewsOps backend is running.
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && (!activities || activities.length === 0) && (
        <div style={{ padding: 32, textAlign: 'center', background: 'var(--surface)', borderRadius: 8, border: '1px solid var(--line)' }}>
          <p style={{ color: 'var(--mute)', fontSize: 14 }}>No agent activities recorded yet for this filter.</p>
          <p style={{ color: 'var(--mute)', fontSize: 12, marginTop: 4 }}>
            Agents log their runs via <code>python scripts/newsops.py activity ...</code>
          </p>
        </div>
      )}

      {/* Activity Timeline List */}
      {!isLoading && !error && activities && activities.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {activities.map((act, idx) => {
            const timeStr = act.created_at ? new Date(act.created_at).toLocaleTimeString() : 'just now'
            const agentColors: Record<string, { bg: string; text: string }> = {
              scout: { bg: 'rgba(59, 130, 246, 0.15)', text: '#2563eb' },
              analyst: { bg: 'rgba(168, 85, 247, 0.15)', text: '#9333ea' },
              editor: { bg: 'rgba(34, 197, 94, 0.15)', text: '#16a34a' },
            }
            const badgeStyle = agentColors[act.agent?.toLowerCase()] || { bg: 'var(--surface2)', text: 'var(--ink)' }

            return (
              <div
                key={act._id || act.id || idx}
                style={{
                  padding: '14px 18px', borderRadius: 8, background: 'var(--surface)',
                  border: '1px solid var(--line)', display: 'flex', alignItems: 'flex-start',
                  gap: 14,
                }}
              >
                {/* Agent Tag */}
                <span
                  style={{
                    padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700,
                    textTransform: 'uppercase', background: badgeStyle.bg, color: badgeStyle.text,
                    flexShrink: 0, marginTop: 2,
                  }}
                >
                  {act.agent}
                </span>

                {/* Content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--mute)' }}>
                      #{act.room}
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--ink)', fontWeight: 600 }}>
                      {act.action}
                    </span>
                    <span style={{ fontSize: 11, color: 'var(--mute)', marginLeft: 'auto' }}>
                      {timeStr}
                    </span>
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--ink)', opacity: 0.85, marginTop: 4, lineHeight: 1.5 }}>
                    {act.message}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </main>
  )
}
