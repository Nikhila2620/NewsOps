'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import Shell from '@/components/Shell'
import { TrustBadge } from '@/components/TrustBadge'
import { PipelineStrip } from '@/components/PipelineStrip'
import { keys, fetchStories, fetchRoomState, repostStory, type Story } from '@/api/queries'
import { useRoomStream } from '@/features/room/useRoomStream'
import { pushToast } from '@/components/Toast'
import { api } from '@/api/client'

const FILTERS = ['All', 'Primary', 'Vendor', 'Community', 'Has install', 'Saved'] as const
type Filter = typeof FILTERS[number]

const ROOMS = ['aiml', 'cloud', 'security']

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      const el = document.createElement('textarea')
      el.value = text; document.body.appendChild(el)
      el.select(); document.execCommand('copy')
      document.body.removeChild(el)
    }
    setCopied(true)
    pushToast({ kind: 'success', message: 'Copied to clipboard' })
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy}
            aria-label="Copy install command"
            style={{
              padding: '2px 8px', fontSize: 11, borderRadius: 4, cursor: 'pointer',
              background: copied ? 'var(--good-bg)' : 'var(--surface2)',
              color: copied ? 'var(--good-fg)' : 'var(--mute)',
              border: '1px solid var(--line)',
            }}>
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

function StoryCard({ story, isNew, onClick }: { story: Story; isNew: boolean; onClick: () => void }) {
  const handleRepost = async (e: React.MouseEvent) => {
    e.stopPropagation()
    const storyId = story._id || (story as any).id
    try {
      await repostStory(storyId, story.room_key)
      pushToast({ kind: 'success', message: `Reposted into #${story.room_key}!` })
    } catch {
      try {
        await api.post(`/rooms/${story.room_key}/messages`, {
          text: `Reposting: ${story.title} — ${story.summary}`,
        })
        pushToast({ kind: 'success', message: 'Reposted to room' })
      } catch {
        pushToast({ kind: 'error', message: 'Repost failed' })
      }
    }
  }

  return (
    <article style={{
      background: 'var(--surface)', borderRadius: 'var(--radius)',
      border: '1px solid var(--line)', padding: '16px 20px',
      display: 'flex', flexDirection: 'column', gap: 10,
      cursor: 'pointer',
    }}
      onClick={onClick}
      tabIndex={0}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick() }}}
      aria-label={`Story: ${story.title}`}>

      {/* Top row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, background: 'var(--surface2)', padding: '2px 8px',
                       borderRadius: 20, color: 'var(--mute)', fontWeight: 600 }}>
          #{story.room_key}
        </span>
        <TrustBadge kind={story.trust_badge} compact />
        {isNew && (
          <span style={{ fontSize: 11, background: 'var(--accent)', color: '#fff',
                         padding: '2px 6px', borderRadius: 20, fontWeight: 700 }}>
            NEW
          </span>
        )}
        <span style={{ fontSize: 11, color: 'var(--mute)', marginLeft: 'auto' }}>
          {story.source_domain} · {new Date(story.published_at).toLocaleDateString()}
        </span>
      </div>

      {/* Title */}
      <h3 style={{ fontFamily: 'Bricolage Grotesque, sans-serif', fontSize: 16,
                   fontWeight: 700, color: 'var(--ink)', lineHeight: 1.3 }}>
        {story.title}
      </h3>

      {/* Summary */}
      <p style={{ fontSize: 13, color: 'var(--mute)', lineHeight: 1.5 }}>{story.summary}</p>

      {/* Impact */}
      {story.impact && (
        <p style={{ fontSize: 12, color: 'var(--ink)', background: 'var(--surface2)',
                    padding: '6px 10px', borderRadius: 6 }}>
          <strong>Affects you:</strong> {story.impact}
        </p>
      )}

      {/* Install command */}
      {story.install_command && (
        <div style={{ background: 'var(--code-bg)', borderRadius: 6, padding: '8px 12px',
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          <code style={{ color: '#e7f0ed', fontSize: 12, flex: 1, wordBreak: 'break-all' }}>
            {story.install_command}
          </code>
          <CopyButton text={story.install_command} />
        </div>
      )}
      {story.install_command && (
        <p style={{ fontSize: 11, color: 'var(--mute)' }}>
          Copied verbatim from the README
          {story.install_commit ? ` · commit ${story.install_commit.slice(0, 7)}` : ''}
          {' '}· never auto-run
        </p>
      )}

      {/* Risk flags */}
      {story.risk_flags?.length > 0 && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {story.risk_flags.map(f => (
            <span key={f} style={{ fontSize: 11, background: 'var(--bad-bg)', color: 'var(--bad-fg)',
                                   padding: '2px 8px', borderRadius: 20, fontWeight: 600 }}>
              ⚠ {f}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
        <Link href={`/stories/${story._id || (story as any).id}`}
              onClick={e => e.stopPropagation()}
              style={{ fontSize: 12, padding: '4px 12px', borderRadius: 6, cursor: 'pointer',
                       background: 'var(--surface2)', color: 'var(--ink)', border: '1px solid var(--line)',
                       textDecoration: 'none' }}>
          Details ↗
        </Link>
        <button onClick={handleRepost}
                style={{ fontSize: 12, padding: '4px 12px', borderRadius: 6, cursor: 'pointer',
                         background: 'var(--surface2)', color: 'var(--ink)', border: '1px solid var(--line)' }}>
          Repost
        </button>
      </div>
    </article>
  )
}

function StoryDrawer({ story, onClose }: { story: Story; onClose: () => void }) {
  const confidence = Math.round((story.confidence ?? 0) * 100)
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 300 }}>
      <div onClick={onClose}
           style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)' }} />
      <aside style={{
        position: 'absolute', right: 0, top: 0, bottom: 0, width: 400,
        background: 'var(--surface)', borderLeft: '1px solid var(--line)',
        overflow: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 16,
      }}
        role="dialog" aria-modal="true" aria-label={`Story detail: ${story.title}`}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <TrustBadge kind={story.trust_badge} />
          <button onClick={onClose} aria-label="Close detail panel"
                  style={{ background: 'none', border: 'none', fontSize: 22,
                           cursor: 'pointer', color: 'var(--mute)' }}>×</button>
        </div>

        <h2 style={{ fontFamily: 'Bricolage Grotesque, sans-serif', fontSize: 20, fontWeight: 800 }}>
          {story.title}
        </h2>
        <p style={{ color: 'var(--mute)', fontSize: 13 }}>{story.summary}</p>

        {/* Confidence meter */}
        <div>
          <div style={{ fontSize: 12, color: 'var(--mute)', marginBottom: 4 }}>
            Confidence: {confidence}%
          </div>
          <div style={{ height: 6, borderRadius: 3, background: 'var(--surface2)', overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: 3,
              width: `${confidence}%`,
              background: confidence >= 80 ? 'var(--good-fg)' : confidence >= 60 ? 'var(--warn-fg)' : 'var(--bad-fg)',
              transition: 'width 0.6s ease',
            }} />
          </div>
        </div>

        {/* Claims */}
        {story.claims && story.claims.length > 0 && (
          <div>
            <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Claims</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {story.claims.map((c, i) => (
                <div key={i} style={{ background: 'var(--surface2)', borderRadius: 8, padding: '8px 12px' }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 4 }}>
                    <span style={{
                      fontSize: 11, padding: '2px 7px', borderRadius: 20, fontWeight: 600, flexShrink: 0,
                      background: c.status === 'supported' ? 'var(--good-bg)'
                                : c.status === 'contradicted' ? 'var(--bad-bg)' : 'var(--warn-bg)',
                      color: c.status === 'supported' ? 'var(--good-fg)'
                           : c.status === 'contradicted' ? 'var(--bad-fg)' : 'var(--warn-fg)',
                    }}>
                      {c.status.charAt(0).toUpperCase() + c.status.slice(1)}
                    </span>
                    <span style={{ fontSize: 13 }}>{c.text}</span>
                  </div>
                  {c.evidence_note && (
                    <p style={{ fontSize: 11, color: 'var(--mute)' }}>{c.evidence_note}</p>
                  )}
                  {c.is_community && (
                    <p style={{ fontSize: 11, color: 'var(--warn-fg)' }}>
                      Community evidence — not counted as sole verification
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </aside>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)',
                  border: '1px solid var(--line)', padding: '16px 20px', height: 140 }}>
      {[80, 100, 60].map((w, i) => (
        <div key={i} style={{
          height: i === 1 ? 18 : 12, width: `${w}%`, borderRadius: 4, marginBottom: 10,
          background: 'var(--surface2)',
          animation: 'shimmer 1.4s ease-in-out infinite',
        }} />
      ))}
      <style>{`
        @keyframes shimmer {
          0%,100% { opacity: 0.5; } 50% { opacity: 1; }
        }
        @media (prefers-reduced-motion: reduce) { * { animation: none !important; } }
      `}</style>
    </div>
  )
}

export default function InboxPage() {
  const [activeRoom] = useState('aiml')
  const [filter, setFilter] = useState<Filter>('All')
  const [selected, setSelected] = useState<Story | null>(null)

  const { step, status: streamStatus, newStoryIds } = useRoomStream(activeRoom)

  const { data: roomState } = useQuery({
    queryKey: keys.state(activeRoom),
    queryFn:  () => fetchRoomState(activeRoom),
    staleTime: 15_000,
  })

  const { data: stories = [], isLoading } = useQuery({
    queryKey: keys.stories(),
    queryFn:  () => fetchStories(),
    staleTime: 30_000,
  })

  const filtered = stories.filter((s: Story) => {
    if (filter === 'Primary')     return s.trust_badge === 'primary'
    if (filter === 'Vendor')      return s.trust_badge === 'vendor_reported'
    if (filter === 'Community')   return s.trust_badge === 'community_signal'
    if (filter === 'Has install') return !!s.install_command
    return true
  })

  return (
    <Shell>
      <div style={{ padding: '24px', maxWidth: 800 }}>
        {/* Greeting */}
        <div style={{ marginBottom: 20 }}>
          <h1 style={{ fontSize: 26, fontWeight: 800, marginBottom: 4 }}>
            Good{new Date().getHours() < 12 ? ' morning' : new Date().getHours() < 18 ? ' afternoon' : ' evening'}
          </h1>
          <p style={{ color: 'var(--mute)', fontSize: 14 }}>
            Verified developer intelligence from #{activeRoom}
          </p>
        </div>

        {/* Pipeline card */}
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)',
                      border: '1px solid var(--line)', padding: '16px 20px', marginBottom: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>
            Pipeline — #{activeRoom}
          </div>
          <PipelineStrip step={roomState?.step ?? step.step}
                          status={roomState?.status ?? streamStatus} />
        </div>

        {/* Filter chips */}
        <div role="group" aria-label="Story filters"
             style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
          {FILTERS.map(f => (
            <button key={f}
                    onClick={() => setFilter(f)}
                    aria-pressed={filter === f}
                    style={{
                      padding: '5px 14px', borderRadius: 20, fontSize: 13, cursor: 'pointer',
                      background: filter === f ? 'var(--accent)' : 'var(--surface)',
                      color: filter === f ? '#fff' : 'var(--ink)',
                      border: `1px solid ${filter === f ? 'var(--accent)' : 'var(--line)'}`,
                      fontWeight: filter === f ? 600 : 400,
                    }}>
              {f}
            </button>
          ))}
        </div>

        {/* Story list */}
        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[1,2,3].map(n => <SkeletonCard key={n} />)}
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--mute)' }}>
            <p style={{ fontSize: 16, marginBottom: 8 }}>No stories yet.</p>
            <p style={{ fontSize: 13 }}>
              Send <code>@scout {activeRoom} last 24h</code> in the room panel to start discovery.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {filtered.map((s: Story) => (
              <StoryCard key={s._id}
                         story={s}
                         isNew={newStoryIds.has(s._id)}
                         onClick={() => setSelected(s)} />
            ))}
          </div>
        )}
      </div>

      {/* Story detail drawer */}
      {selected && <StoryDrawer story={selected} onClose={() => setSelected(null)} />}
    </Shell>
  )
}
