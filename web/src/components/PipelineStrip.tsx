import type { FC } from 'react'

interface Props {
  step: number  // -1 idle, 1 scout, 2 analyst, 3 editor, 4 approver
  status: string
}

const NODES = [
  { id: 1, label: 'Scout',    color: 'var(--scout)'   },
  { id: 2, label: 'Analyst',  color: 'var(--analyst)' },
  { id: 3, label: 'Editor',   color: 'var(--editor)'  },
  { id: 4, label: 'Approver', color: 'var(--ink)'     },
]

export const PipelineStrip: FC<Props> = ({ step, status }) => {
  return (
    <div role="img" aria-label={`Pipeline: step ${step}, status ${status}`}
         style={{ display: 'flex', alignItems: 'center', gap: 0, padding: '12px 0' }}>
      {NODES.map((n, i) => {
        const isDone   = step > n.id || (step === n.id && status === 'done')
        const isActive = step === n.id && status === 'running'
        const isPending = step < n.id && step !== -1 ? false : step === -1

        return (
          <div key={n.id} style={{ display: 'flex', alignItems: 'center' }}>
            {/* Node */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
              <div style={{
                width: 36, height: 36, borderRadius: '50%',
                background: isDone ? n.color : isActive ? n.color : 'var(--surface2)',
                border: `2px solid ${isDone || isActive ? n.color : 'var(--line)'}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: isDone || isActive ? '#fff' : 'var(--mute)',
                fontSize: 14,
                // Pulse animation for active (respects reduced motion via globals.css)
                animation: isActive ? 'pulse 1.5s ease-in-out infinite' : 'none',
                boxShadow: isActive ? `0 0 0 4px color-mix(in srgb, ${n.color} 30%, transparent)` : 'none',
                transition: 'all 0.3s ease',
              }}>
                {isDone ? '✓' : n.id}
              </div>
              <span style={{ fontSize: 11, color: isActive ? n.color : isDone ? 'var(--ink)' : 'var(--mute)',
                             fontWeight: isActive ? 700 : 400 }}>
                {n.label}
              </span>
            </div>
            {/* Wire between nodes */}
            {i < NODES.length - 1 && (
              <div style={{
                width: 32, height: 2, marginBottom: 14,
                background: step > n.id ? n.color : 'var(--line)',
                transition: 'background 0.4s ease',
                position: 'relative', overflow: 'hidden',
              }}>
                {isActive && (
                  <div style={{
                    position: 'absolute', top: 0, left: '-100%',
                    width: '100%', height: '100%',
                    background: `linear-gradient(90deg, transparent, ${n.color}, transparent)`,
                    animation: 'wire-flow 1s linear infinite',
                  }} />
                )}
              </div>
            )}
          </div>
        )
      })}
      <style>{`
        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 0 4px transparent; }
          50% { box-shadow: 0 0 0 6px color-mix(in srgb, currentColor 25%, transparent); }
        }
        @keyframes wire-flow {
          from { left: -100%; }
          to   { left:  100%; }
        }
        @media (prefers-reduced-motion: reduce) {
          * { animation: none !important; }
        }
      `}</style>
    </div>
  )
}
