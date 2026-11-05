'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchStories, type Story } from '@/api/queries'
import { TrustBadge } from '@/components/TrustBadge'
import { pushToast } from '@/components/Toast'

export default function ToolsPage() {
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const { data: rawStories, isLoading, error } = useQuery<Story[]>({
    queryKey: ['stories', 'tools'],
    queryFn: () => fetchStories(),
  })

  // Normalize stories payload (handles array or { items: [] })
  const stories: Story[] = Array.isArray(rawStories)
    ? rawStories
    : (rawStories as any)?.items || []

  // Filter stories that have install commands or tools
  const toolStories = stories.filter(s => s.install_command || s.source_domain?.includes('github'))

  const copyCmd = (id: string, cmd: string) => {
    navigator.clipboard.writeText(cmd)
    setCopiedId(id)
    pushToast({ kind: 'success', message: 'Install command copied!' })
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <main style={{ padding: '24px 16px', maxWidth: 960, margin: '0 auto', width: '100%' }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, color: 'var(--ink)' }}>
          Developer Tools & Verified Packages
        </h1>
        <p style={{ fontSize: 13, color: 'var(--mute)', marginTop: 4 }}>
          Curated open-source libraries, runtimes, and tools extracted deterministically with verbatim install commands.
        </p>
      </div>

      {isLoading && (
        <div style={{ padding: 24, background: 'var(--surface)', borderRadius: 8, color: 'var(--mute)', fontSize: 14 }}>
          Loading developer tools...
        </div>
      )}

      {error && (
        <div style={{ padding: 24, background: 'var(--surface)', borderRadius: 8, color: 'var(--error)', fontSize: 14 }}>
          Failed to load tools catalog.
        </div>
      )}

      {!isLoading && !error && toolStories.length === 0 && (
        <div style={{ padding: 32, textAlign: 'center', background: 'var(--surface)', borderRadius: 8 }}>
          <p style={{ color: 'var(--mute)', fontSize: 14 }}>No tools found in current story catalog.</p>
        </div>
      )}

      {!isLoading && !error && toolStories.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
          {toolStories.map(tool => (
            <div
              key={tool._id}
              style={{
                background: 'var(--surface)', padding: 18, borderRadius: 10,
                border: '1px solid var(--line)', display: 'flex', flexDirection: 'column',
                justifyContent: 'space-between', gap: 12,
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--mute)', textTransform: 'uppercase' }}>
                    #{tool.room_key}
                  </span>
                  <TrustBadge kind={tool.trust_badge || 'primary'} />
                </div>

                <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--ink)', lineHeight: 1.3, marginBottom: 8 }}>
                  {tool.title}
                </h3>

                <p style={{ fontSize: 12, color: 'var(--mute)', lineHeight: 1.5, marginBottom: 12 }}>
                  {tool.summary}
                </p>
              </div>

              <div>
                {tool.install_command && (
                  <div style={{ background: 'var(--bg)', padding: '8px 10px', borderRadius: 6, border: '1px solid var(--line)', marginBottom: 10 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <code style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--ink)', overflowX: 'auto' }}>
                        {tool.install_command}
                      </code>
                      <button
                        onClick={() => copyCmd(tool._id, tool.install_command!)}
                        style={{
                          padding: '2px 8px', fontSize: 11, borderRadius: 4, cursor: 'pointer',
                          background: copiedId === tool._id ? 'var(--accent)' : 'var(--surface2)',
                          color: copiedId === tool._id ? '#fff' : 'var(--ink)',
                          border: '1px solid var(--line)', fontWeight: 600, flexShrink: 0, marginLeft: 6,
                        }}
                      >
                        {copiedId === tool._id ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                  </div>
                )}

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 12 }}>
                  {tool.source_url ? (
                    <a href={tool.source_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent)', textDecoration: 'underline' }}>
                      Open Repository ↗
                    </a>
                  ) : (
                    <span style={{ color: 'var(--mute)' }}>GitHub package</span>
                  )}
                  {tool.commit_sha && (
                    <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--mute)' }}>
                      sha: {tool.commit_sha.slice(0, 7)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  )
}
