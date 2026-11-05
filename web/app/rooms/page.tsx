'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchRooms, sendRoomInvite, type Room } from '@/api/queries'
import { pushToast } from '@/components/Toast'

export default function RoomsPage() {
  const queryClient = useQueryClient()
  const [selectedRoom, setSelectedRoom] = useState<string>('aiml')
  const [inviteeHandle, setInviteeHandle] = useState('')
  const mattermostUrl = process.env.NEXT_PUBLIC_MATTERMOST_URL

  const { data: rooms, isLoading, error } = useQuery<Room[]>({
    queryKey: ['rooms'],
    queryFn: fetchRooms,
  })

  const inviteMutation = useMutation({
    mutationFn: ({ roomKey, handle }: { roomKey: string; handle: string }) =>
      sendRoomInvite(roomKey, handle),
    onSuccess: () => {
      pushToast({ kind: 'success', message: `Invitation sent to @${inviteeHandle.replace('@', '')}!` })
      setInviteeHandle('')
    },
    onError: (err: any) => {
      pushToast({ kind: 'error', message: err?.message || 'Could not send invitation.' })
    },
  })

  const handleSendInvite = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inviteeHandle.trim()) return
    inviteMutation.mutate({ roomKey: selectedRoom, handle: inviteeHandle.trim() })
  }

  return (
    <main style={{ padding: '24px 16px', maxWidth: 960, margin: '0 auto', width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, color: 'var(--ink)' }}>
            Topic Rooms & Member Management
          </h1>
          <p style={{ fontSize: 13, color: 'var(--mute)', marginTop: 4 }}>
            Switch platform rooms monitored by autonomous Scout, Analyst, and Editor agents.
          </p>
        </div>

        {mattermostUrl && (
          <a
            href={mattermostUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              padding: '6px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600,
              background: '#1d4ed8', color: '#fff', textDecoration: 'none',
              display: 'inline-flex', alignItems: 'center', gap: 6,
            }}
          >
            💬 Open in Mattermost ↗
          </a>
        )}
      </div>

      {isLoading && (
        <div style={{ padding: 24, background: 'var(--surface)', borderRadius: 8, color: 'var(--mute)', fontSize: 14 }}>
          Loading active rooms...
        </div>
      )}

      {error && (
        <div style={{ padding: 24, background: 'var(--surface)', borderRadius: 8, color: 'var(--error)', fontSize: 14 }}>
          Could not fetch room directory.
        </div>
      )}

      {!isLoading && !error && rooms && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16, marginBottom: 28 }}>
          {rooms.map(room => (
            <div
              key={room._id || room.key}
              style={{
                background: 'var(--surface)', padding: 20, borderRadius: 10,
                border: '1px solid var(--line)', display: 'flex', flexDirection: 'column', gap: 12,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h3 style={{ fontSize: 16, fontWeight: 800, color: 'var(--ink)' }}>
                  #{room.key}
                </h3>
                <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'var(--surface2)', color: 'var(--mute)' }}>
                  {room.name}
                </span>
              </div>

              <div>
                <span style={{ fontSize: 12, color: 'var(--mute)', fontWeight: 600 }}>Topics:</span>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
                  {room.topics?.map(t => (
                    <span key={t} style={{ fontSize: 11, padding: '2px 6px', borderRadius: 4, background: 'var(--bg)', border: '1px solid var(--line)' }}>
                      {t}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <span style={{ fontSize: 12, color: 'var(--mute)', fontWeight: 600 }}>Designated Approvers:</span>
                <div style={{ fontSize: 12, color: 'var(--ink)', marginTop: 4 }}>
                  {room.approvers && room.approvers.length > 0 ? (
                    room.approvers.map(a => `@${a.replace('@', '')}`).join(', ')
                  ) : (
                    <span style={{ color: 'var(--mute)' }}>None designated</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Invite Member Section */}
      <section style={{ background: 'var(--surface)', padding: 22, borderRadius: 10, border: '1px solid var(--line)' }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--ink)', marginBottom: 8 }}>
          Send Room Invitation
        </h3>
        <p style={{ fontSize: 13, color: 'var(--mute)', marginBottom: 16 }}>
          Invite developers or teammates to review and monitor intelligence in a specific room.
        </p>

        <form onSubmit={handleSendInvite} style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <select
            value={selectedRoom}
            onChange={e => setSelectedRoom(e.target.value)}
            style={{
              padding: '8px 12px', borderRadius: 6, fontSize: 13,
              background: 'var(--bg)', color: 'var(--ink)', border: '1px solid var(--line)',
            }}
          >
            <option value="aiml">#aiml (AI/ML)</option>
            <option value="cloud">#cloud (Cloud & Platform)</option>
            <option value="security">#security (Security & Supply Chain)</option>
          </select>

          <input
            type="text"
            placeholder="@github_handle or chat handle"
            value={inviteeHandle}
            onChange={e => setInviteeHandle(e.target.value)}
            style={{
              flex: 1, minWidth: 200, padding: '8px 12px', borderRadius: 6, fontSize: 13,
              background: 'var(--bg)', color: 'var(--ink)', border: '1px solid var(--line)',
            }}
          />

          <button
            type="submit"
            disabled={inviteMutation.isPending || !inviteeHandle.trim()}
            style={{
              padding: '8px 16px', borderRadius: 6, fontSize: 13, fontWeight: 600,
              background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer',
              opacity: (!inviteeHandle.trim() || inviteMutation.isPending) ? 0.6 : 1,
            }}
          >
            {inviteMutation.isPending ? 'Sending...' : 'Send Invite'}
          </button>
        </form>
      </section>
    </main>
  )
}
