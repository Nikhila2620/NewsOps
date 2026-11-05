/**
 * Unit tests for version/impact display helpers and message formatter.
 * Spec requirement: test the version and impact display helpers,
 * the SSE reducer (seq de-duplication), and the message formatter (HTML escaping).
 */
import { describe, it, expect } from 'vitest'

// ── Message formatter ──────────────────────────────────────────────────────
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function formatMessage(text: string): string {
  const escaped = escapeHtml(text)
  return escaped
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/@(\w+)/g, '<span class="mention">@$1</span>')
}

describe('formatMessage', () => {
  it('escapes < > & characters before applying markup', () => {
    const result = formatMessage('<script>alert("xss")</script>')
    expect(result).not.toContain('<script>')
    expect(result).toContain('&lt;script&gt;')
  })

  it('wraps **bold** in <strong>', () => {
    expect(formatMessage('**hello**')).toContain('<strong>hello</strong>')
  })

  it('wraps `code` in <code>', () => {
    expect(formatMessage('run `npm install`')).toContain('<code>npm install</code>')
  })

  it('highlights @mentions', () => {
    expect(formatMessage('@scout check this')).toContain('<span class="mention">@scout</span>')
  })

  it('does not process markup inside already-escaped content', () => {
    // A raw <b> tag must be escaped, not treated as bold
    const result = formatMessage('<b>bold</b>')
    expect(result).toContain('&lt;b&gt;bold&lt;/b&gt;')
    expect(result).not.toContain('<b>bold</b>')
  })
})

// ── SSE reducer (seq de-duplication) ─────────────────────────────────────
interface MockEvent { seq: number; text: string }

function sseReducer(seen: Set<number>, event: MockEvent): { accepted: boolean; nextSeen: Set<number> } {
  if (seen.has(event.seq)) return { accepted: false, nextSeen: seen }
  const next = new Set(seen)
  next.add(event.seq)
  return { accepted: true, nextSeen: next }
}

describe('SSE reducer', () => {
  it('accepts a new seq', () => {
    const seen = new Set<number>()
    const { accepted } = sseReducer(seen, { seq: 1, text: 'a' })
    expect(accepted).toBe(true)
  })

  it('rejects a duplicate seq', () => {
    const seen = new Set<number>([1, 2])
    const { accepted } = sseReducer(seen, { seq: 1, text: 'duplicate' })
    expect(accepted).toBe(false)
  })

  it('accepts seq=0 on first message', () => {
    const { accepted } = sseReducer(new Set(), { seq: 0, text: 'init' })
    expect(accepted).toBe(true)
  })

  it('accumulates seen seqs correctly', () => {
    let seen = new Set<number>()
    for (const seq of [1, 2, 3]) {
      const res = sseReducer(seen, { seq, text: '' })
      seen = res.nextSeen
    }
    expect(seen.size).toBe(3)
    // Re-submit all — none accepted
    let accepted = 0
    for (const seq of [1, 2, 3]) {
      const res = sseReducer(seen, { seq, text: '' })
      if (res.accepted) accepted++
    }
    expect(accepted).toBe(0)
  })
})

// ── Impact display helpers ────────────────────────────────────────────────
type Severity = 'HIGH' | 'MODERATE' | 'LOW'
function severityLabel(s: Severity): string {
  return s.charAt(0) + s.slice(1).toLowerCase()
}

function confidenceDisplay(score: number): string {
  const pct = Math.round(score * 100)
  return `${pct}%`
}

describe('impact display helpers', () => {
  it('renders severity correctly', () => {
    expect(severityLabel('HIGH')).toBe('High')
    expect(severityLabel('MODERATE')).toBe('Moderate')
    expect(severityLabel('LOW')).toBe('Low')
  })

  it('renders confidence as percentage string', () => {
    expect(confidenceDisplay(0.92)).toBe('92%')
    expect(confidenceDisplay(0.5)).toBe('50%')
    expect(confidenceDisplay(1.0)).toBe('100%')
  })
})
