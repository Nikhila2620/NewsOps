/**
 * useRoomStream — live SSE hook for a NewsOps room.
 *
 * Spec compliance:
 * - Fetches /rooms/{key}/state + /activity?after_seq=0 on mount, then opens SSE
 * - Tracks lastSeq; on reconnect uses after_seq=lastSeq (no lost / duplicate events)
 * - De-duplicates by seq
 * - Exponential backoff 1s → 15s; after 3 failures falls back to polling /activity every 3s
 * - Exposes { messages, step, status, connection } + newStoryIds
 * - Invalidates stories and digest queries on 'stories' and 'digest' events
 */

'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import { useQueryClient }  from '@tanstack/react-query'
import { API_BASE, getToken } from '@/api/client'
import { keys } from '@/api/queries'

export type ConnectionState = 'live' | 'reconnecting' | 'polling' | 'offline'

export interface RoomMessage {
  seq: number
  type: 'message' | 'step' | 'digest' | 'stories'
  who?: string
  text?: string
  handoff?: string
  card?: unknown
  blocked?: boolean
  user_name?: string
  system?: boolean
  // sending state (optimistic)
  _state?: 'sending' | 'confirmed' | 'failed'
  _localId?: string
}

export interface StepState {
  step: number   // -1 idle, 0-3 agents, 4 approver
  status: 'idle' | 'running' | 'done' | 'rejected'
}

interface UseRoomStreamResult {
  messages: RoomMessage[]
  step: StepState
  status: string
  connection: ConnectionState
  newStoryIds: Set<string>
  send: (text: string) => Promise<void>
}

export function useRoomStream(roomKey: string): UseRoomStreamResult {
  const qc = useQueryClient()
  const [messages, setMessages]   = useState<RoomMessage[]>([])
  const [step, setStep]           = useState<StepState>({ step: -1, status: 'idle' })
  const [connection, setConn]     = useState<ConnectionState>('reconnecting')
  const [newStoryIds, setNewIds]  = useState<Set<string>>(new Set())

  const seenSeqs   = useRef<Set<number>>(new Set())
  const lastSeq    = useRef(0)
  const esRef      = useRef<EventSource | null>(null)
  const backoff    = useRef(1000)
  const failures   = useRef(0)
  const pollTimer  = useRef<ReturnType<typeof setInterval> | null>(null)
  const mounted    = useRef(true)

  const applyEvent = useCallback((raw: RoomMessage) => {
    if (!mounted.current) return
    if (raw.seq && seenSeqs.current.has(raw.seq)) return
    if (raw.seq) {
      seenSeqs.current.add(raw.seq)
      lastSeq.current = Math.max(lastSeq.current, raw.seq)
    }

    if (raw.type === 'step') {
      const stepNum = (raw as unknown as { step: number; status: string }).step ?? -1
      const st = (raw as unknown as { status: string }).status ?? 'idle'
      setStep({ step: stepNum, status: st as StepState['status'] })
      return
    }

    if (raw.type === 'stories') {
      const ids: string[] = (raw as unknown as { added: string[] }).added ?? []
      setNewIds(prev => new Set([...Array.from(prev), ...ids]))
      qc.invalidateQueries({ queryKey: keys.stories() })
      return
    }

    if (raw.type === 'digest') {
      qc.invalidateQueries({ queryKey: keys.digest(roomKey) })
      qc.invalidateQueries({ queryKey: keys.state(roomKey) })
      return
    }

    if (raw.type === 'message' || raw.type === undefined) {
      setMessages(prev => [...prev, { ...raw, type: 'message' }])
    }
  }, [qc, roomKey])

  // ── Fetch initial state + backlog ──────────────────────────────────────
  const loadBacklog = useCallback(async () => {
    try {
      const base = API_BASE
      const token = getToken()
      const qs = token ? `?access_token=${token}` : ''
      const [, actRes] = await Promise.all([
        fetch(`${base}/rooms/${roomKey}/state`),
        fetch(`${base}/activity?room_key=${roomKey}&after_seq=0${qs ? '&' + qs.slice(1) : ''}`),
      ])
      if (actRes.ok) {
        const data = await actRes.json()
        ;(data.events ?? []).forEach(applyEvent)
      }
    } catch {}
  }, [roomKey, applyEvent])

  // ── Open SSE ────────────────────────────────────────────────────────────
  const openSSE = useCallback(() => {
    if (!mounted.current) return
    esRef.current?.close()

    const token = getToken()
    const url = `${API_BASE}/events?room_key=${roomKey}&after_seq=${lastSeq.current}${token ? `&access_token=${token}` : ''}`
    const es = new EventSource(url)
    esRef.current = es

    const handleEvent = (ev: MessageEvent, type: string) => {
      try {
        const data = JSON.parse(ev.data)
        applyEvent({ ...data, type: type as RoomMessage['type'] })
      } catch {}
    }

    es.addEventListener('message', e => handleEvent(e, 'message'))
    es.addEventListener('step',    e => handleEvent(e, 'step'))
    es.addEventListener('digest',  e => handleEvent(e, 'digest'))
    es.addEventListener('stories', e => handleEvent(e, 'stories'))

    es.onopen = () => {
      if (!mounted.current) return
      failures.current = 0
      backoff.current  = 1000
      setConn('live')
      // Stop polling if it was running
      if (pollTimer.current) { clearInterval(pollTimer.current); pollTimer.current = null }
    }

    es.onerror = () => {
      if (!mounted.current) return
      es.close()
      failures.current++
      setConn('reconnecting')

      if (failures.current >= 3) {
        // Fall back to polling
        setConn('polling')
        if (!pollTimer.current) {
          pollTimer.current = setInterval(async () => {
            if (!mounted.current) return
            try {
              const base = API_BASE
              const token = getToken()
              const res = await fetch(`${base}/activity?room_key=${roomKey}&after_seq=${lastSeq.current}${token ? `&access_token=${token}` : ''}`)
              if (res.ok) {
                const data = await res.json()
                ;(data.events ?? []).forEach(applyEvent)
              }
            } catch {}
          }, 3000)
        }
        // Keep trying SSE in the background
        setTimeout(openSSE, 15000)
        return
      }

      const delay = Math.min(backoff.current, 15000)
      backoff.current = Math.min(backoff.current * 2, 15000)
      setTimeout(openSSE, delay)
    }
  }, [roomKey, applyEvent])

  useEffect(() => {
    mounted.current = true
    loadBacklog().then(openSSE)
    return () => {
      mounted.current = false
      esRef.current?.close()
      if (pollTimer.current) clearInterval(pollTimer.current)
    }
  }, [roomKey, loadBacklog, openSSE])

  // ── Send a message (optimistic) ─────────────────────────────────────────
  const send = useCallback(async (text: string) => {
    const localId = `local-${Date.now()}`
    const optimistic: RoomMessage = {
      seq: -1,
      type: 'message',
      who: 'me',
      text,
      _state: 'sending',
      _localId: localId,
    }
    setMessages(prev => [...prev, optimistic])

    try {
      const token = getToken()
      const res = await fetch(`${API_BASE}/rooms/${roomKey}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, access_token: token }),
      })
      if (!res.ok) throw new Error('send failed')
      const data = await res.json()
      // Confirm the optimistic message
      setMessages(prev =>
        prev.map(m => m._localId === localId
          ? { ...m, seq: data.seq, _state: 'confirmed' }
          : m
        )
      )
    } catch {
      setMessages(prev =>
        prev.map(m => m._localId === localId
          ? { ...m, _state: 'failed' }
          : m
        )
      )
    }
  }, [roomKey])

  return { messages, step, status: step.status, connection, newStoryIds, send }
}
