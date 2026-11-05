'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Shell from '@/components/Shell'
import { keys, fetchRadar, voteRadar, type RadarItem } from '@/api/queries'
import { pushToast } from '@/components/Toast'
import { ApiError } from '@/api/client'

const RINGS = ['adopt', 'trial', 'assess', 'hold'] as const
type Ring = typeof RINGS[number]
const RING_COLORS: Record<Ring, string> = {
  adopt:  '#0d7f57',
  trial:  '#4850d4',
  assess: '#8f5b00',
  hold:   '#c0263a',
}
const RING_RADII = { adopt: 60, trial: 110, assess: 160, hold: 210 }
const ROOM_ANGLES: Record<string, number> = { aiml: 0, cloud: 120, security: 240 }
const CENTER = 230

/** Deterministic placement within a sector and ring */
function blipPosition(item: RadarItem, index: number) {
  const baseAngle = (ROOM_ANGLES[item.room_key] ?? 0) + (index * 23) % 100
  const r = RING_RADII[item.ring as Ring] ?? 150
  const spread = 35
  const angle = ((baseAngle + 10) / 180) * Math.PI
  return {
    x: CENTER + (r + (index % 3) * spread * 0.4) * Math.cos(angle),
    y: CENTER + (r + (index % 3) * spread * 0.4) * Math.sin(angle),
  }
}

export default function RadarPage() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<RadarItem | null>(null)

  const { data: items = [], isLoading } = useQuery({
    queryKey: keys.radar(),
    queryFn:  fetchRadar,
    staleTime: 30_000,
  })

  const vote = useMutation({
    mutationFn: ({ id, ring }: { id: string; ring: string }) => voteRadar(id, ring),
    onSuccess: (updated) => {
      qc.setQueryData(keys.radar(), (prev: RadarItem[] | undefined) =>
        (prev ?? []).map(i => i._id === updated._id ? updated : i)
      )
      setSelected(updated)
    },
    onError: (e) => {
      pushToast({ kind: 'error', message: e instanceof ApiError ? e.message : 'Vote failed' })
    },
  })

  return (
    <Shell>
      <div style={{ padding: 24, display: 'flex', gap: 24, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 16 }}>Tech Radar</h1>

          {isLoading ? (
            <div style={{ width: 460, height: 460, background: 'var(--surface)',
                          borderRadius: '50%', display: 'flex', alignItems: 'center',
                          justifyContent: 'center', color: 'var(--mute)' }}>
              Loading…
            </div>
          ) : (
            <svg width={460} height={460} viewBox="0 0 460 460"
                 role="img" aria-label="Technology radar with 4 rings and 3 room sectors">
              {/* Rings */}
              {(Object.entries(RING_RADII) as [Ring, number][]).reverse().map(([ring, r]) => (
                <circle key={ring} cx={CENTER} cy={CENTER} r={r}
                        fill="none" stroke="var(--line)" strokeWidth={1} />
              ))}
              {/* Ring labels */}
              {(Object.entries(RING_RADII) as [Ring, number][]).map(([ring, r]) => (
                <text key={ring} x={CENTER + r - 5} y={CENTER - 4}
                      fill="var(--mute)" fontSize={10} textAnchor="end">
                  {ring.toUpperCase()}
                </text>
              ))}
              {/* Sector lines */}
              {Object.entries(ROOM_ANGLES).map(([room, deg]) => {
                const a = (deg / 180) * Math.PI
                return (
                  <line key={room}
                        x1={CENTER} y1={CENTER}
                        x2={CENTER + 220 * Math.cos(a)} y2={CENTER + 220 * Math.sin(a)}
                        stroke="var(--line)" strokeWidth={1} strokeDasharray="4 4" />
                )
              })}
              {/* Blips */}
              {(items as RadarItem[]).map((item, i) => {
                const pos = blipPosition(item, i)
                const isSelected = selected?._id === item._id
                return (
                  <g key={item._id}
                     transform={`translate(${pos.x},${pos.y})`}
                     style={{ cursor: 'pointer', transition: 'transform 0.4s ease' }}
                     tabIndex={0}
                     role="button"
                     aria-label={`${item.name} — ${item.ring}`}
                     onClick={() => setSelected(item)}
                     onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setSelected(item) }}>
                    <circle r={10}
                            fill={isSelected ? 'var(--accent)' : RING_COLORS[item.ring as Ring]}
                            stroke={isSelected ? 'var(--ink)' : 'none'}
                            strokeWidth={2} />
                    <text textAnchor="middle" dy="4" fontSize={9}
                          fill="#fff" fontWeight={700}>
                      {i + 1}
                    </text>
                  </g>
                )
              })}
            </svg>
          )}

          {/* Legend */}
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 8 }}>
            {RINGS.map(r => (
              <div key={r} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%',
                              background: RING_COLORS[r] }} />
                {r.charAt(0).toUpperCase() + r.slice(1)}
              </div>
            ))}
          </div>
        </div>

        {/* Side panel */}
        {selected ? (
          <div style={{ flex: 1, minWidth: 240, background: 'var(--surface)',
                        borderRadius: 'var(--radius)', border: '1px solid var(--line)',
                        padding: 20, alignSelf: 'flex-start' }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{selected.name}</h2>
            <span style={{ fontSize: 12, color: RING_COLORS[selected.ring as Ring],
                           fontWeight: 700, textTransform: 'uppercase' }}>
              {selected.ring}
            </span>
            {selected.description && (
              <p style={{ fontSize: 13, color: 'var(--mute)', marginTop: 8 }}>
                {selected.description}
              </p>
            )}

            {/* Vote bars */}
            <div style={{ marginTop: 16 }}>
              <p style={{ fontSize: 12, fontWeight: 700, marginBottom: 8 }}>Votes by ring</p>
              {RINGS.map(r => {
                const count = selected.votes?.[r] ?? 0
                const total = Object.values(selected.votes ?? {}).reduce((a, b) => a + b, 0) || 1
                return (
                  <div key={r} style={{ marginBottom: 6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between',
                                  fontSize: 12, marginBottom: 2 }}>
                      <span>{r}</span><span>{count}</span>
                    </div>
                    <div style={{ height: 4, background: 'var(--surface2)', borderRadius: 2 }}>
                      <div style={{ width: `${(count / total) * 100}%`, height: '100%',
                                    background: RING_COLORS[r], borderRadius: 2,
                                    transition: 'width 0.4s ease' }} />
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Vote buttons */}
            <div style={{ marginTop: 16 }}>
              <p style={{ fontSize: 12, fontWeight: 700, marginBottom: 8 }}>Your vote</p>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {RINGS.map(r => (
                  <button key={r}
                          onClick={() => vote.mutate({ id: selected._id, ring: r })}
                          aria-pressed={selected.user_vote === r}
                          style={{
                            padding: '5px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
                            border: `1px solid ${RING_COLORS[r]}`,
                            background: selected.user_vote === r ? RING_COLORS[r] : 'transparent',
                            color: selected.user_vote === r ? '#fff' : RING_COLORS[r],
                            fontWeight: 600,
                          }}>
                    {r}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ flex: 1, minWidth: 200, display: 'flex', alignItems: 'center',
                        justifyContent: 'center', color: 'var(--mute)', fontSize: 14 }}>
            Click a blip to see details and vote
          </div>
        )}
      </div>
    </Shell>
  )
}
