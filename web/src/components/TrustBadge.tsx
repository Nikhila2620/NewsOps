import type { FC } from 'react'

type Kind = 'primary' | 'vendor_reported' | 'community_signal'

const CONFIG: Record<Kind, { label: string; fg: string; bg: string; icon: string; tooltip: string }> = {
  primary: {
    label: 'Primary',
    fg: 'var(--good-fg)', bg: 'var(--good-bg)',
    icon: '✓',
    tooltip: 'Verified from a primary authoritative source (official release, CVE, documentation)',
  },
  vendor_reported: {
    label: 'Vendor-reported',
    fg: 'var(--vendor-fg)', bg: 'var(--vendor-bg)',
    icon: '🛡',
    tooltip: 'Reported by the vendor; independently corroborated where possible',
  },
  community_signal: {
    label: 'Community signal',
    fg: 'var(--warn-fg)', bg: 'var(--warn-bg)',
    icon: '💬',
    tooltip: 'Community-sourced signal. Not counted as sole verification evidence.',
  },
}

interface Props {
  kind: Kind
  compact?: boolean
}

export const TrustBadge: FC<Props> = ({ kind, compact }) => {
  const c = CONFIG[kind]
  return (
    <span
      title={c.tooltip}
      aria-label={`Trust level: ${c.label}. ${c.tooltip}`}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        background: c.bg, color: c.fg,
        padding: compact ? '1px 6px' : '2px 8px',
        borderRadius: 20, fontSize: compact ? 11 : 12,
        fontWeight: 600, whiteSpace: 'nowrap',
      }}>
      <span aria-hidden="true">{c.icon}</span>
      {!compact && c.label}
    </span>
  )
}
