'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchStory, type Story } from '@/api/queries'
import { api } from '@/api/client'
import { TrustBadge } from '@/components/TrustBadge'
import { pushToast } from '@/components/Toast'

export default function StoryDetailPage() {
  const params = useParams()
  const id = Array.isArray(params?.id) ? params.id[0] : (params?.id as string)
  const queryClient = useQueryClient()
  const [copied, setCopied] = useState(false)
  const [feedbackSent, setFeedbackSent] = useState<string | null>(null)

  const { data: story, isLoading, error } = useQuery<Story>({
    queryKey: ['story', id],
    queryFn: () => fetchStory(id),
    enabled: Boolean(id),
  })

  const feedbackMutation = useMutation({
    mutationFn: (type: 'relevant' | 'irrelevant' | 'correction') =>
      api.post(`/stories/${id}/feedback`, { type, comment: `User clicked ${type}` }),
    onSuccess: (_, type) => {
      setFeedbackSent(type)
      pushToast({ kind: 'success', message: `Feedback '${type}' recorded!` })
    },
    onError: () => {
      pushToast({ kind: 'error', message: 'Could not record feedback.' })
    },
  })

  const copyCommand = (cmd: string) => {
    navigator.clipboard.writeText(cmd)
    setCopied(true)
    pushToast({ kind: 'success', message: 'Command copied to clipboard!' })
    setTimeout(() => setCopied(false), 2000)
  }

  if (isLoading) {
    return (
      <main style={{ padding: 24, maxWidth: 860, margin: '0 auto' }}>
        <div style={{ color: 'var(--mute)', fontSize: 14 }}>Loading story intelligence...</div>
      </main>
    )
  }

  if (error || !story) {
    return (
      <main style={{ padding: 24, maxWidth: 860, margin: '0 auto' }}>
        <div style={{ background: 'var(--surface)', padding: 24, borderRadius: 8, border: '1px solid var(--line)' }}>
          <h2 style={{ fontSize: 18, color: 'var(--error)' }}>Story Not Found</h2>
          <p style={{ color: 'var(--mute)', marginTop: 8 }}>The requested story intelligence is unavailable or has not been ingested.</p>
          <Link href="/" style={{ display: 'inline-block', marginTop: 16, color: 'var(--accent)', textDecoration: 'underline' }}>
            ← Back to Inbox
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main style={{ padding: '24px 16px', maxWidth: 860, margin: '0 auto', width: '100%' }}>
      {/* Back button */}
      <div style={{ marginBottom: 16 }}>
        <Link href="/" style={{ color: 'var(--mute)', fontSize: 13, textDecoration: 'none' }}>
          ← Back to Inbox
        </Link>
      </div>

      {/* Header */}
      <div style={{ background: 'var(--surface)', padding: 24, borderRadius: 10, border: '1px solid var(--line)', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
          <span style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: 'var(--mute)' }}>
            #{story.room_key || 'tech'}
          </span>
          <TrustBadge kind={story.trust_badge || 'community_signal'} />
          {story.seeded && (
            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 9999, background: 'rgba(245, 158, 11, 0.15)', color: '#d97706', border: '1px solid rgba(245, 158, 11, 0.3)', fontWeight: 600 }}>
              seeded
            </span>
          )}
          {story.confidence !== undefined && (
            <span style={{ fontSize: 12, color: 'var(--mute)', marginLeft: 'auto' }}>
              Confidence: {Math.round(story.confidence * 100)}%
            </span>
          )}
        </div>

        <h1 style={{ fontSize: 22, fontWeight: 800, color: 'var(--ink)', lineHeight: 1.3, marginBottom: 12 }}>
          {story.title}
        </h1>

        <p style={{ fontSize: 14, color: 'var(--ink)', opacity: 0.85, lineHeight: 1.6, marginBottom: 16 }}>
          {story.summary}
        </p>

        {story.source_url && (
          <div style={{ fontSize: 13, color: 'var(--mute)' }}>
            Source:{' '}
            <a href={story.source_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent)', textDecoration: 'underline' }}>
              {story.source_domain || story.source_url} ↗
            </a>
          </div>
        )}
      </div>

      {/* Install & Try Block (Verbatim README Substring) */}
      {story.install_command && (
        <section style={{ background: 'var(--surface)', padding: 20, borderRadius: 10, border: '1px solid var(--line)', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)' }}>
              ⚡ Install & Try (Verbatim Extracted Command)
            </h3>
            {story.commit_sha && (
              <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--mute)' }}>
                commit: {story.commit_sha.slice(0, 7)}
              </span>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', background: 'var(--bg)', padding: '10px 14px', borderRadius: 6, border: '1px solid var(--line)', gap: 10 }}>
            <code style={{ flex: 1, fontFamily: 'monospace', fontSize: 13, color: 'var(--ink)', overflowX: 'auto' }}>
              {story.install_command}
            </code>
            <button
              onClick={() => copyCommand(story.install_command!)}
              style={{
                padding: '4px 10px', fontSize: 12, borderRadius: 4, cursor: 'pointer',
                background: copied ? 'var(--accent)' : 'var(--surface2)',
                color: copied ? '#fff' : 'var(--ink)', border: '1px solid var(--line)',
                fontWeight: 600, flexShrink: 0,
              }}
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>

          {/* Risk Flags in Red */}
          {story.risk_flags && story.risk_flags.length > 0 && (
            <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: '#ef4444' }}>⚠️ Risk Flags:</span>
              {story.risk_flags.map((flag, idx) => (
                <span
                  key={idx}
                  style={{
                    fontSize: 11, padding: '2px 8px', borderRadius: 4,
                    background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444',
                    border: '1px solid rgba(239, 68, 68, 0.3)', fontWeight: 600,
                  }}
                >
                  {flag}
                </span>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Claims and Evidence */}
      <section style={{ background: 'var(--surface)', padding: 20, borderRadius: 10, border: '1px solid var(--line)', marginBottom: 20 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 12 }}>
          🔍 Extracted Claims & Multi-Tier Evidence
        </h3>

        {(!story.claims || story.claims.length === 0) ? (
          <p style={{ color: 'var(--mute)', fontSize: 13 }}>No atomic claims isolated for this story cluster.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {story.claims.map((claim, idx) => (
              <div
                key={idx}
                style={{
                  padding: 12, borderRadius: 6, background: 'var(--bg)',
                  border: '1px solid var(--line)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                  <span style={{ fontSize: 13, color: 'var(--ink)', fontWeight: 500 }}>
                    {claim.text}
                  </span>
                  <span
                    style={{
                      fontSize: 11, padding: '2px 6px', borderRadius: 4, textTransform: 'uppercase',
                      fontWeight: 700,
                      background: claim.status === 'supported' ? 'rgba(34, 197, 94, 0.15)' :
                                  claim.status === 'contradicted' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(234, 179, 8, 0.15)',
                      color: claim.status === 'supported' ? '#16a34a' :
                             claim.status === 'contradicted' ? '#dc2626' : '#ca8a04',
                    }}
                  >
                    {claim.status}
                  </span>
                </div>
                {claim.evidence_note && (
                  <p style={{ fontSize: 12, color: 'var(--mute)', marginTop: 4 }}>
                    Note: {claim.evidence_note}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Evidence Artifacts */}
        {story.evidence && story.evidence.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <h4 style={{ fontSize: 13, fontWeight: 600, color: 'var(--mute)', marginBottom: 8 }}>
              Evidence Links
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {story.evidence.map((ev, idx) => (
                <div key={idx} style={{ fontSize: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span style={{ color: 'var(--mute)', textTransform: 'capitalize' }}>[{ev.evidence_type.replace('_', ' ')}]</span>
                  <a
                    href={ev.evidence_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--accent)', textDecoration: 'underline' }}
                  >
                    {ev.source_reference || ev.evidence_url} ↗
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Analyst Synthesis */}
      {story.analysis && (
        <section style={{ background: 'var(--surface)', padding: 20, borderRadius: 10, border: '1px solid var(--line)', marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 12 }}>
            🤖 Analyst Narrative Synthesis
          </h3>
          <p style={{ fontSize: 13, color: 'var(--ink)', lineHeight: 1.6, marginBottom: 8 }}>
            {story.analysis.summary}
          </p>
          {story.analysis.why_it_matters && (
            <p style={{ fontSize: 13, color: 'var(--mute)', lineHeight: 1.5 }}>
              <strong>Why it matters:</strong> {story.analysis.why_it_matters}
            </p>
          )}
        </section>
      )}

      {/* Human Feedback Buttons */}
      <section style={{ background: 'var(--surface)', padding: 16, borderRadius: 10, border: '1px solid var(--line)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <span style={{ fontSize: 13, color: 'var(--mute)', fontWeight: 500 }}>
          Is this intelligence relevant to your stack?
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => feedbackMutation.mutate('relevant')}
            disabled={feedbackMutation.isPending || feedbackSent === 'relevant'}
            style={{
              padding: '6px 12px', fontSize: 12, borderRadius: 6, cursor: 'pointer',
              border: '1px solid var(--line)', background: feedbackSent === 'relevant' ? '#16a34a' : 'var(--surface2)',
              color: feedbackSent === 'relevant' ? '#fff' : 'var(--ink)', fontWeight: 600,
            }}
          >
            👍 Relevant
          </button>
          <button
            onClick={() => feedbackMutation.mutate('irrelevant')}
            disabled={feedbackMutation.isPending || feedbackSent === 'irrelevant'}
            style={{
              padding: '6px 12px', fontSize: 12, borderRadius: 6, cursor: 'pointer',
              border: '1px solid var(--line)', background: feedbackSent === 'irrelevant' ? '#dc2626' : 'var(--surface2)',
              color: feedbackSent === 'irrelevant' ? '#fff' : 'var(--ink)', fontWeight: 600,
            }}
          >
            👎 Irrelevant
          </button>
          <button
            onClick={() => feedbackMutation.mutate('correction')}
            disabled={feedbackMutation.isPending || feedbackSent === 'correction'}
            style={{
              padding: '6px 12px', fontSize: 12, borderRadius: 6, cursor: 'pointer',
              border: '1px solid var(--line)', background: 'var(--surface2)',
              color: 'var(--ink)', fontWeight: 600,
            }}
          >
            ✏️ Suggest Correction
          </button>
        </div>
      </section>
    </main>
  )
}
