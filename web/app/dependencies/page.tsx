'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import Shell from '@/components/Shell'
import { scanImpact, saveProject, type AdvisoryRow } from '@/api/queries'
import { pushToast } from '@/components/Toast'
import { ApiError } from '@/api/client'

const SAMPLE_PY = `requests==2.28.0
pillow==9.5.0
numpy==1.24.0
fastapi==0.104.1
uvicorn==0.24.0
`

const SAMPLE_JSON = `{
  "dependencies": {
    "lodash": "4.17.20",
    "axios": "1.5.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "express": "4.18.0"
  }
}`

const SEVERITY_COLORS: Record<string, { bg: string; fg: string }> = {
  HIGH:     { bg: 'var(--bad-bg)',    fg: 'var(--bad-fg)' },
  MODERATE: { bg: 'var(--warn-bg)',   fg: 'var(--warn-fg)' },
  LOW:      { bg: 'var(--vendor-bg)', fg: 'var(--vendor-fg)' },
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try { await navigator.clipboard.writeText(text) } catch {}
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <button onClick={copy}
            style={{ padding: '2px 8px', fontSize: 11, cursor: 'pointer', borderRadius: 4,
                     background: 'var(--surface2)', border: '1px solid var(--line)',
                     color: copied ? 'var(--good-fg)' : 'var(--mute)' }}>
      {copied ? '✓' : 'Copy'}
    </button>
  )
}

export default function DependenciesPage() {
  const [content, setContent] = useState('')
  const [result, setResult] = useState<Awaited<ReturnType<typeof scanImpact>> | null>(null)

  const scan = useMutation({
    mutationFn: async (text: string) => {
      const r = await scanImpact(text)
      await saveProject(text).catch(() => {})
      return r
    },
    onSuccess: data => {
      setResult(data)
      pushToast({ kind: 'success', message: `Scan complete — ${data.affected} affected packages` })
    },
    onError: e => {
      pushToast({ kind: 'error', message: e instanceof ApiError ? e.message : 'Scan failed' })
    },
  })

  const statusColor = (s: AdvisoryRow['status']) =>
    s === 'affected' ? { bg: 'var(--bad-bg)', fg: 'var(--bad-fg)' }
    : s === 'possible' ? { bg: 'var(--warn-bg)', fg: 'var(--warn-fg)' }
    : { bg: 'var(--good-bg)', fg: 'var(--good-fg)' }

  return (
    <Shell>
      <div style={{ padding: 24, maxWidth: 860 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 4 }}>Dependency Impact</h1>
        <p style={{ color: 'var(--mute)', fontSize: 14, marginBottom: 20 }}>
          Paste your <code>requirements.txt</code> or <code>package.json</code> to scan for known advisories.
        </p>

        {/* Quick-fill sample buttons */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <button onClick={() => setContent(SAMPLE_PY)}
                  style={{ fontSize: 12, padding: '4px 10px', borderRadius: 6, cursor: 'pointer',
                           background: 'var(--surface2)', border: '1px solid var(--line)', color: 'var(--ink)' }}>
            Load sample requirements.txt
          </button>
          <button onClick={() => setContent(SAMPLE_JSON)}
                  style={{ fontSize: 12, padding: '4px 10px', borderRadius: 6, cursor: 'pointer',
                           background: 'var(--surface2)', border: '1px solid var(--line)', color: 'var(--ink)' }}>
            Load sample package.json
          </button>
        </div>

        <textarea
          value={content}
          onChange={e => setContent(e.target.value)}
          placeholder="Paste requirements.txt or package.json here…"
          aria-label="Dependency file content"
          rows={8}
          style={{
            width: '100%', fontFamily: 'JetBrains Mono, monospace', fontSize: 13,
            background: 'var(--code-bg)', color: '#e7f0ed',
            border: '1px solid var(--line)', borderRadius: 10, padding: '12px 16px',
            resize: 'vertical', outline: 'none',
          }}
        />

        <button onClick={() => scan.mutate(content)}
                disabled={!content.trim() || scan.isPending}
                style={{
                  marginTop: 12, padding: '10px 24px', borderRadius: 8, fontSize: 14,
                  background: 'var(--accent)', color: '#fff', border: 'none',
                  cursor: content.trim() ? 'pointer' : 'not-allowed',
                  opacity: content.trim() ? 1 : 0.5, fontWeight: 700,
                }}>
          {scan.isPending ? 'Scanning…' : 'Scan'}
        </button>

        {/* Results */}
        {result && (
          <div style={{ marginTop: 24 }}>
            {/* Summary tiles */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
              {[
                { label: 'Affected',          count: result.affected,  bg: 'var(--bad-bg)',    fg: 'var(--bad-fg)' },
                { label: 'Possible exposure', count: result.possible,  bg: 'var(--warn-bg)',   fg: 'var(--warn-fg)' },
                { label: 'Clear',             count: result.clear,     bg: 'var(--good-bg)',   fg: 'var(--good-fg)' },
              ].map(t => (
                <div key={t.label}
                     style={{ background: t.bg, color: t.fg, borderRadius: 12,
                              padding: '12px 20px', minWidth: 120, textAlign: 'center' }}>
                  <div style={{ fontSize: 28, fontWeight: 800 }}>{t.count}</div>
                  <div style={{ fontSize: 12 }}>{t.label}</div>
                </div>
              ))}
              {result.source === 'sample' && (
                <div style={{ alignSelf: 'center', fontSize: 12, color: 'var(--mute)',
                              background: 'var(--surface2)', padding: '6px 12px', borderRadius: 8 }}>
                  Sample advisories (offline mode)
                </div>
              )}
            </div>

            {/* Table */}
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--line)', textAlign: 'left' }}>
                    {['Package','Status','Advisory','Severity','Summary','Fix'].map(h => (
                      <th key={h} style={{ padding: '8px 12px', color: 'var(--mute)',
                                           fontWeight: 600, fontSize: 11, whiteSpace: 'nowrap' }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.items.map((row, i) => {
                    const sc = statusColor(row.status)
                    return (
                      <tr key={i} style={{ borderBottom: '1px solid var(--line)' }}>
                        <td style={{ padding: '10px 12px', fontFamily: 'JetBrains Mono, monospace',
                                     fontWeight: 600 }}>{row.package}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{ background: sc.bg, color: sc.fg, padding: '2px 8px',
                                         borderRadius: 20, fontSize: 11, fontWeight: 600 }}>
                            {row.status}
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', fontFamily: 'JetBrains Mono, monospace',
                                     fontSize: 11, color: 'var(--mute)' }}>
                          {row.advisory_id ?? '—'}
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          {row.severity ? (
                            <span style={{
                              background: SEVERITY_COLORS[row.severity]?.bg ?? 'var(--surface2)',
                              color: SEVERITY_COLORS[row.severity]?.fg ?? 'var(--mute)',
                              padding: '2px 7px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                            }}>
                              {row.severity}
                            </span>
                          ) : '—'}
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--mute)', maxWidth: 240 }}>
                          {row.summary ?? '—'}
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          {row.fix ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <code style={{ fontSize: 11, background: 'var(--code-bg)',
                                             color: '#e7f0ed', padding: '2px 6px', borderRadius: 4 }}>
                                {row.fix}
                              </code>
                              <CopyButton text={row.fix} />
                            </div>
                          ) : '—'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </Shell>
  )
}
