/**
 * TanStack Query keys and query/mutation functions for every API resource.
 */
import { api } from './client'

// ─── Query key factory ────────────────────────────────────────────────────
export const keys = {
  stories:      (filters?: Record<string, unknown>) => ['stories', filters ?? {}] as const,
  story:        (id: string)  => ['story', id] as const,
  digest:       (room: string) => ['digest', room] as const,
  digestById:   (id: string)  => ['digestById', id] as const,
  state:        (room: string) => ['state', room] as const,
  radar:        ()            => ['radar'] as const,
  radarItem:    (id: string)  => ['radarItem', id] as const,
  me:           ()            => ['me'] as const,
  rooms:        ()            => ['rooms'] as const,
  room:         (key: string) => ['room', key] as const,
  sources:      ()            => ['sources'] as const,
  switchStatus: ()            => ['switchStatus'] as const,
  healthz:      ()            => ['healthz'] as const,
}

// ─── Stories ──────────────────────────────────────────────────────────────
export interface Story {
  _id: string
  title: string
  summary: string
  source_domain: string
  published_at: string
  room_key: string
  trust_badge: 'primary' | 'vendor_reported' | 'community_signal'
  confidence: number
  impact?: string
  risk_flags: string[]
  install_command?: string
  install_commit?: string
  claims?: ClaimItem[]
  score?: number
}

export interface ClaimItem {
  text: string
  status: 'supported' | 'unconfirmed' | 'contradicted'
  evidence_note?: string
  is_community?: boolean
}

export const fetchStories = (params?: Record<string, string>) => {
  const qs = params ? '?' + new URLSearchParams(params).toString() : ''
  return api.get<Story[]>(`/stories${qs}`)
}

export const fetchStory = (id: string) => api.get<Story>(`/stories/${id}`)

// ─── Digests ──────────────────────────────────────────────────────────────
export interface DigestItem {
  story_id: string
  position: number
  editor_note?: string
  included: boolean
}

export interface ApprovalRecord {
  reviewer: string
  decision: string
  comment?: string
  source: string
  at: string
}

export interface Digest {
  _id: string
  room_key: string
  status: 'draft' | 'review_required' | 'approved' | 'rejected' | 'published'
  created_at: string
  published_at?: string
  items: DigestItem[]
  approvals: ApprovalRecord[]
  version: number
}

export const fetchDigests = (room_key: string) =>
  api.get<Digest[]>(`/digests?room_key=${room_key}`)

export const fetchDigestById = (id: string) => api.get<Digest>(`/digests/${id}`)

export const approveDigest   = (id: string, comment?: string) =>
  api.post<Digest>(`/digests/${id}/approve`, comment ? { comment } : undefined)

export const rejectDigest    = (id: string, comment?: string) =>
  api.post<Digest>(`/digests/${id}/reject`, comment ? { comment } : undefined)

export const requestChanges  = (id: string, comment?: string) =>
  api.post<Digest>(`/digests/${id}/request-changes`, comment ? { comment } : undefined)

export const publishDigest   = (id: string) =>
  api.post<Digest>(`/digests/${id}/publish`)

export const patchDigestItem = (id: string, storyId: string, included: boolean) =>
  api.patch<Digest>(`/digests/${id}/items/${storyId}`, { included })

// ─── Room state ───────────────────────────────────────────────────────────
export interface RoomState {
  room_key: string
  room_name: string
  step: number
  status: string
  agents: string[]
  approvers: string[]
  chat_channel_id: string
  digest?: { id: string; status: string; item_count: number } | null
  last_seq: number
}

export const fetchRoomState = (key: string) =>
  api.get<RoomState>(`/rooms/${key}/state`)

// ─── Rooms ────────────────────────────────────────────────────────────────
export interface Room {
  _id: string
  key: string
  name: string
  topics: string[]
  approvers: string[]
  chat_channel_id: string
}

export const fetchRooms = () => api.get<Room[]>('/rooms')

// ─── Radar ────────────────────────────────────────────────────────────────
export interface RadarItem {
  _id: string
  name: string
  room_key: string
  ring: 'adopt' | 'trial' | 'assess' | 'hold'
  description?: string
  votes: Record<string, number>   // ring → count
  user_vote?: string | null
}

export const fetchRadar = () => api.get<RadarItem[]>('/radar/items')
export const voteRadar  = (id: string, ring: string) =>
  api.post<RadarItem>(`/radar/items/${id}/votes`, { ring })

// ─── Me / Auth ────────────────────────────────────────────────────────────
export interface Me {
  _id: string
  display_name: string
  chat_handle: string
  topics: string[]
  experience: string
  approver_rooms?: string[]
}

export const fetchMe = () => api.get<Me>('/me')

export const demoLogin = (persona: 'alice' | 'sam') =>
  api.post<{ token: string; user_id: string; chat_handle: string; display_name: string; approver_rooms: string[] }>(
    '/auth/demo-login', { persona },
  )

// ─── Switch / Health ──────────────────────────────────────────────────────
export const fetchSwitchStatus = () => api.get<{ connected: boolean; is_mock?: boolean }>('/switch/status')
export const fetchHealthz      = () => api.get<{ status: string }>('/healthz')

// ─── Impact scan ──────────────────────────────────────────────────────────
export interface AdvisoryRow {
  package: string
  status: 'affected' | 'possible' | 'clear'
  advisory_id?: string
  severity?: string
  summary?: string
  fix?: string
  source: string
}

export interface ScanResult {
  ecosystem: string
  total: number
  affected: number
  possible: number
  clear: number
  items: AdvisoryRow[]
  source: string
}

export const scanImpact = (content: string) =>
  api.post<ScanResult>('/impact/scan', { content })

export const saveProject = (content: string, filename?: string) =>
  api.put('/me/project', { content, filename })

// ─── Demo reset ───────────────────────────────────────────────────────────
export const resetDemo = () => api.post('/demo/reset')
