'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Shell from '@/components/Shell'
import { TrustBadge } from '@/components/TrustBadge'
import { PipelineStrip } from '@/components/PipelineStrip'
import {
  keys, fetchDigests, fetchRoomState, patchDigestItem,
  approveDigest, rejectDigest, requestChanges, publishDigest,
  type Digest,
} from '@/api/queries'
import { pushToast } from '@/components/Toast'
import { ApiError, getToken } from '@/api/client'
import { usePersona } from '@/hooks/usePersona'
import { api } from '@/api/client'

const ROOMS = ['aiml', 'cloud', 'security']

function useActiveRoom() {
  const [room, setRoom] = useState('aiml')
  return { room, setRoom }
}

export default function ReviewPage() {
  const { room, setRoom } = useActiveRoom()
  const { persona } = usePersona()
  const qc = useQueryClient()

  const { data: digests = [], isLoading } = useQuery({
    queryKey: keys.digest(room),
    queryFn:  () => fetchDigests(room),
    staleTime: 15_000,
  })

  const { data: roomState } = useQuery({
    queryKey: keys.state(room),
    queryFn:  () => fetchRoomState(room),
    staleTime: 15_000,
  })

  const digest: Digest | undefined = digests[0]
  const canApprove = persona?.approver_rooms?.includes(room) ?? false

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: keys.digest(room) })
    qc.invalidateQueries({ queryKey: keys.state(room) })
  }

  const withError = async (label: string, fn: () => Promise<unknown>) => {
    try {
      await fn()
      pushToast({ kind: 'success', message: `${label} successful` })
      invalidate()
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : `${label} failed`
      pushToast({ kind: 'error', message: msg })
      // Still invalidate — blocked attempt is part of the audit trail
      invalidate()
    }
  }

  const [reason, setReason] = useState('')

  const approve   = useMutation({ mutationFn: (id: string) => approveDigest(id, reason || 'Approved via dashboard'),
    onSuccess: () => { pushToast({ kind: 'success', message: 'Digest approved' }); invalidate(); setReason('') },
    onError: e => { pushToast({ kind: 'error', message: e instanceof ApiError ? e.message : 'Approve failed' }); invalidate() }
  })
  const reject    = useMutation({ mutationFn: (id: string) => rejectDigest(id, reason || 'Rejected via dashboard'),
    onSuccess: () => { pushToast({ kind: 'success', message: 'Digest rejected' }); invalidate(); setReason('') },
    onError: e => { pushToast({ kind: 'error', message: e instanceof ApiError ? e.message : 'Reject failed' }); invalidate() }
  })
  const reqChange = useMutation({ mutationFn: (id: string) => requestChanges(id),
    onSuccess: () => { pushToast({ kind: 'success', message: 'Changes requested' }); invalidate() },
    onError: e => { pushToast({ kind: 'error', message: e instanceof ApiError ? e.message : 'Request failed' }); invalidate() }
  })
  const publish   = useMutation({ mutationFn: (id: string) => publishDigest(id),
    onSuccess: () => { pushToast({ kind: 'success', message: 'Digest published!' }); invalidate() },
    onError: e => { pushToast({ kind: 'error', message: e instanceof ApiError ? `403 · ${e.message}` : 'Publish failed' }); invalidate() }
  })

  const patchItem = useMutation({
    mutationFn: ({ id, storyId, included }: { id: string; storyId: string; included: boolean }) =>
      patchDigestItem(id, storyId, included),
    onSuccess: () => invalidate(),
  })

  const sendScout = async () => {
    try {
      await api.post(`/rooms/${room}/messages`, { text: `@scout ${room} last 24h` })
      pushToast({ kind: 'success', message: `@scout triggered in #${room}` })
    } catch {
      pushToast({ kind: 'error', message: 'Failed to send to room' })
    }
  }

  const STATUS_LABELS: Record<string, string> = {
    draft:           'Draft',
    review_required: 'Review required',
    approved:        'Approved',
    rejected:        'Rejected',
    published:       'Published',
  }
  const STATUS_COLORS: Record<string, { bg: string; fg: string }> = {
    draft:           { bg: 'var(--surface2)', fg: 'var(--mute)' },
    review_required: { bg: 'var(--warn-bg)',  fg: 'var(--warn-fg)' },
    approved:        { bg: 'var(--good-bg)',  fg: 'var(--good-fg)' },
    rejected:        { bg: 'var(--bad-bg)',   fg: 'var(--bad-fg)' },
    published:       { bg: 'var(--good-bg)',  fg: 'var(--good-fg)' },
  }

  return (
    <Shell>
      <div style={{ padding: 24, maxWidth: 860 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 16 }}>Review</h1>

        {/* Room selector */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {ROOMS.map(r => (
            <button key={r} onClick={() => setRoom(r)}
                    aria-pressed={room === r}
                    style={{
                      padding: '5px 14px', borderRadius: 20, fontSize: 13, cursor: 'pointer',
                      background: room === r ? 'var(--accent)' : 'var(--surface)',
                      color: room === r ? '#fff' : 'var(--ink)',
                      border: `1px solid ${room === r ? 'var(--accent)' : 'var(--line)'}`,
                      fontWeight: room === r ? 600 : 400,
                    }}>
              #{r}
            </button>
          ))}
        </div>

        {/* Pipeline strip */}
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)',
                      border: '1px solid var(--line)', padding: '16px 20px', marginBottom: 16 }}>
          <PipelineStrip step={roomState?.step ?? -1} status={roomState?.status ?? 'idle'} />
        </div>

        {/* Gate bar */}
        <div style={{
          background: canApprove ? 'var(--good-bg)' : 'var(--bad-bg)',
          color: canApprove ? 'var(--good-fg)' : 'var(--bad-fg)',
          borderRadius: 8, padding: '8px 16px', fontSize: 13, marginBottom: 16,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span>{canApprove ? '✓' : '✗'}</span>
          <span>
            {persona ? (
              canApprove
                ? `Logged in as ${persona.display_name} — you can approve #${room}`
                : `Logged in as ${persona.display_name} — approving #${room} will return 403`
            ) : 'Not logged in — switch persona above to test approval'}
          </span>
        </div>

        {isLoading ? (
          <p style={{ color: 'var(--mute)' }}>Loading…</p>
        ) : !digest ? (
          <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--mute)' }}>
            <p style={{ marginBottom: 12 }}>No digest yet for #{room}.</p>
            <button onClick={sendScout}
                    style={{ padding: '8px 20px', borderRadius: 8, background: 'var(--accent)',
                             color: '#fff', border: 'none', cursor: 'pointer', fontSize: 14 }}>
              Send @scout to #{room}
            </button>
          </div>
        ) : (
          <>
            {/* Digest header */}
            <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)',
                          border: '1px solid var(--line)', padding: 20, marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between',
                            alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
                <div>
                  <div suppressHydrationWarning style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4 }}>
                    Digest v{digest.version} · {new Date(digest.created_at).toLocaleString()}
                  </div>
                  <span style={{
                    ...STATUS_COLORS[digest.status],
                    padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600,
                  }}>
                    {STATUS_LABELS[digest.status]}
                  </span>
                </div>

                {/* Reason input and Action buttons */}
                {(digest.status === 'review_required' || digest.status === 'draft') && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12, width: '100%' }}>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <input
                        type="text"
                        placeholder="Reason or editorial notes (optional)"
                        value={reason}
                        onChange={e => setReason(e.target.value)}
                        style={{
                          flex: 1, minWidth: 220, padding: '6px 12px', borderRadius: 6,
                          fontSize: 13, background: 'var(--bg)', color: 'var(--ink)',
                          border: '1px solid var(--line)',
                        }}
                      />
                      <button onClick={() => reqChange.mutate(digest._id)}
                              style={{ padding: '7px 14px', borderRadius: 7, fontSize: 13,
                                       cursor: 'pointer', border: '1px solid var(--line)',
                                       background: 'var(--surface2)', color: 'var(--ink)' }}>
                        Request changes
                      </button>
                      <button onClick={() => reject.mutate(digest._id)}
                              style={{ padding: '7px 14px', borderRadius: 7, fontSize: 13,
                                       cursor: 'pointer', border: '1px solid var(--bad-fg)',
                                       background: 'var(--bad-bg)', color: 'var(--bad-fg)' }}>
                        Reject
                      </button>
                      <button onClick={() => approve.mutate(digest._id)}
                              style={{ padding: '7px 14px', borderRadius: 7, fontSize: 13,
                                       cursor: 'pointer', border: '1px solid var(--good-fg)',
                                       background: 'var(--good-bg)', color: 'var(--good-fg)',
                                       fontWeight: 700 }}>
                        Approve
                      </button>
                    </div>
                    {roomState?.approvers && roomState.approvers.length > 0 && (
                      <div style={{ fontSize: 11, color: 'var(--mute)' }}>
                        Authorized Approvers: {roomState.approvers.map(a => `@${a.replace('@', '')}`).join(', ')}
                      </div>
                    )}
                  </div>
                )}
                {digest.status === 'approved' && (
                  <button onClick={() => publish.mutate(digest._id)}
                          style={{ padding: '7px 18px', borderRadius: 7, fontSize: 13,
                                   cursor: 'pointer', border: 'none',
                                   background: 'var(--accent)', color: '#fff', fontWeight: 700 }}>
                    Approve and publish
                  </button>
                )}
              </div>
            </div>

            {/* Digest items */}
            {digest.items.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>Digest items</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {digest.items.map((item, i) => (
                    <div key={item.story_id}
                         style={{ background: 'var(--surface)', borderRadius: 10,
                                  border: '1px solid var(--line)', padding: '12px 16px',
                                  display: 'flex', justifyContent: 'space-between',
                                  alignItems: 'center', gap: 12, flexWrap: 'wrap',
                                  opacity: item.included ? 1 : 0.5 }}>
                      <div>
                        <div style={{ fontSize: 12, color: 'var(--mute)', marginBottom: 2 }}>
                          #{i + 1} · {item.story_id}
                        </div>
                        {item.editor_note && (
                          <p style={{ fontSize: 12, color: 'var(--warn-fg)' }}>
                            ⚠ Needs your decision: {item.editor_note}
                          </p>
                        )}
                      </div>
                      {item.editor_note && (
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button onClick={() => patchItem.mutate(
                                    { id: digest._id, storyId: item.story_id, included: true })}
                                  aria-pressed={item.included}
                                  style={{ padding: '4px 12px', borderRadius: 6, fontSize: 12,
                                           cursor: 'pointer', border: 'none',
                                           background: item.included ? 'var(--good-bg)' : 'var(--surface2)',
                                           color: item.included ? 'var(--good-fg)' : 'var(--mute)' }}>
                            Keep
                          </button>
                          <button onClick={() => patchItem.mutate(
                                    { id: digest._id, storyId: item.story_id, included: false })}
                                  aria-pressed={!item.included}
                                  style={{ padding: '4px 12px', borderRadius: 6, fontSize: 12,
                                           cursor: 'pointer', border: 'none',
                                           background: !item.included ? 'var(--bad-bg)' : 'var(--surface2)',
                                           color: !item.included ? 'var(--bad-fg)' : 'var(--mute)' }}>
                            Remove
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Audit trail */}
            {digest.approvals.length > 0 && (
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>Audit trail</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {digest.approvals.map((a, i) => (
                    <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'center',
                                          fontSize: 13, padding: '8px 12px',
                                          background: 'var(--surface)', borderRadius: 8,
                                          border: '1px solid var(--line)' }}>
                      <span style={{ fontWeight: 600 }}>{a.reviewer}</span>
                      <span style={{
                        padding: '1px 8px', borderRadius: 20, fontSize: 11,
                        background: a.decision === 'approved' ? 'var(--good-bg)'
                                  : a.decision === 'rejected' ? 'var(--bad-bg)' : 'var(--warn-bg)',
                        color: a.decision === 'approved' ? 'var(--good-fg)'
                             : a.decision === 'rejected' ? 'var(--bad-fg)' : 'var(--warn-fg)',
                      }}>
                        {a.decision}
                      </span>
                      {a.comment && <span style={{ color: 'var(--mute)' }}>{a.comment}</span>}
                      <span suppressHydrationWarning style={{ marginLeft: 'auto', color: 'var(--mute)', fontSize: 11 }}>
                        {new Date(a.at).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </Shell>
  )
}
