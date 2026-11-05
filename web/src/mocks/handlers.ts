/**
 * MSW request handlers for mock mode (NEXT_PUBLIC_MOCK=1).
 * Reproduces the demo sequence: @scout message triggers Scout → Analyst → Editor pipeline.
 */
import { http, HttpResponse, delay } from 'msw'

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000/api/v1'

// ── Sample data ───────────────────────────────────────────────────────────

const STORIES = [
  {
    _id: 'story-mock-001',
    title: 'LangChain 0.3 drops Python 3.8 support and ships async-first APIs',
    summary: 'The 0.3 release removes deprecated sync wrappers and makes async the default execution path.',
    source_domain: 'github.com',
    published_at: new Date(Date.now() - 3600000).toISOString(),
    room_key: 'aiml',
    trust_badge: 'primary',
    confidence: 0.92,
    risk_flags: [],
    install_command: 'pip install langchain==0.3.0',
    install_commit: 'abc1234defg',
    claims: [
      { text: 'Python 3.8 support dropped', status: 'supported', evidence_note: 'Confirmed in CHANGELOG.md' },
      { text: 'Async is now the default', status: 'supported', evidence_note: 'Official blog post' },
    ],
  },
  {
    _id: 'story-mock-002',
    title: 'CRITICAL: requests library SSRF via redirect following (CVE-2024-1234)',
    summary: 'A server-side request forgery vulnerability allows proxy-authorization header leakage on redirects.',
    source_domain: 'github.com',
    published_at: new Date(Date.now() - 7200000).toISOString(),
    room_key: 'security',
    trust_badge: 'primary',
    confidence: 0.97,
    risk_flags: ['CVE', 'SSRF', 'HIGH'],
    impact: 'Any service using requests with proxy auth is potentially affected',
    install_command: 'pip install "requests>=2.31.0"',
    claims: [
      { text: 'Proxy-Authorization header leaks on 301 redirects', status: 'supported', evidence_note: 'CVE database entry' },
    ],
  },
  {
    _id: 'story-mock-003',
    title: 'Kubernetes 1.31 promotes sidecar containers to stable',
    summary: 'Sidecar containers — native init containers that run for the full pod lifetime — are now GA.',
    source_domain: 'kubernetes.io',
    published_at: new Date(Date.now() - 86400000).toISOString(),
    room_key: 'cloud',
    trust_badge: 'vendor_reported',
    confidence: 0.88,
    risk_flags: [],
    install_command: 'kubectl version --short',
    claims: [
      { text: 'Sidecar containers promoted to stable', status: 'supported' },
    ],
  },
]

const RADAR_ITEMS = [
  { _id: 'radar-001', name: 'LangChain', room_key: 'aiml', ring: 'trial', description: 'LLM orchestration framework', votes: { adopt: 3, trial: 8, assess: 2, hold: 0 }, user_vote: null },
  { _id: 'radar-002', name: 'Kubernetes Sidecars', room_key: 'cloud', ring: 'adopt', description: 'Native sidecar containers GA', votes: { adopt: 12, trial: 3, assess: 1, hold: 0 }, user_vote: null },
  { _id: 'radar-003', name: 'OSV Scanner', room_key: 'security', ring: 'assess', description: 'Open source vulnerability scanner', votes: { adopt: 5, trial: 4, assess: 6, hold: 1 }, user_vote: null },
]

let _radarItems: Array<{
  _id: string; name: string; room_key: string; ring: string
  description: string; votes: Record<string, number>; user_vote: string | null
}> = RADAR_ITEMS.map(i => ({ ...i }))

// ── Handlers ──────────────────────────────────────────────────────────────

export const handlers = [
  // Health
  http.get(`${BASE}/healthz`, () =>
    HttpResponse.json({ status: 'ok', is_mock: true })
  ),

  // Auth
  http.post(`${BASE}/auth/demo-login`, async ({ request }) => {
    const body = await request.json() as { persona: string }
    if (body.persona === 'alice') {
      return HttpResponse.json({ token: 'mock-alice', user_id: 'user-001', chat_handle: 'alice_aiml',
                                  display_name: 'Alice Chen', approver_rooms: ['aiml','security'] })
    }
    return HttpResponse.json({ token: 'mock-sam', user_id: 'user-sam-001', chat_handle: 'sam_cloud',
                                display_name: 'Sam Rivera', approver_rooms: ['cloud'] })
  }),

  // Me
  http.get(`${BASE}/me`, () =>
    HttpResponse.json({ _id: 'user-001', display_name: 'Alice Chen', chat_handle: 'alice_aiml',
                        topics: ['aiml'], experience: 'senior', approver_rooms: ['aiml','security'] })
  ),

  // Stories
  http.get(`${BASE}/stories`, () => HttpResponse.json(STORIES)),

  // Radar
  http.get(`${BASE}/radar/items`, () => HttpResponse.json(_radarItems)),
  http.post(`${BASE}/radar/items/:id/votes`, async ({ params, request }) => {
    const { id } = params
    const body = await request.json() as { ring: string }
    _radarItems = _radarItems.map(item => {
      if (item._id !== id) return item
      const votes: Record<string, number> = { ...item.votes }
      if (item.user_vote) votes[item.user_vote] = Math.max(0, (votes[item.user_vote] ?? 0) - 1)
      votes[body.ring] = (votes[body.ring] ?? 0) + 1
      return { ...item, ring: body.ring, votes, user_vote: body.ring }
    })
    return HttpResponse.json(_radarItems.find(i => i._id === id))
  }),

  // Impact scan
  http.post(`${BASE}/impact/scan`, async ({ request }) => {
    const body = await request.json() as { content: string }
    await delay(800)
    const items = body.content.includes('requests') ? [
      { package: 'requests', status: 'affected', advisory_id: 'GHSA-j8r2-6x86-q33q',
        severity: 'HIGH', summary: 'SSRF via proxy-authorization header leak',
        fix: 'pip install "requests>=2.31.0"', source: 'sample' },
    ] : []
    return HttpResponse.json({
      ecosystem: 'pypi', total: 3, affected: items.length,
      possible: 0, clear: 3 - items.length, items, source: 'sample',
    })
  }),

  // Rooms
  http.get(`${BASE}/rooms`, () => HttpResponse.json([
    { _id: 'room-aiml-001', key: 'aiml', name: 'AI/ML Intelligence', topics: ['aiml'],
      approvers: ['alice_aiml'], chat_channel_id: 'channel-aiml' },
  ])),
  http.get(`${BASE}/rooms/:key/state`, ({ params }) =>
    HttpResponse.json({ room_key: params.key, room_name: params.key, step: -1,
                        status: 'idle', agents: ['scout','analyst','editor'],
                        approvers: ['alice_aiml'], chat_channel_id: '', digest: null, last_seq: 0 })
  ),

  // Digests
  http.get(`${BASE}/digests`, () => HttpResponse.json([])),

  // Switch status
  http.get(`${BASE}/switch/status`, () =>
    HttpResponse.json({ connected: false, is_mock: true })
  ),

  // Demo reset
  http.post(`${BASE}/demo/reset`, () =>
    HttpResponse.json({ reset: true, message: 'Mock reset.' })
  ),

  // Activity (SSE fallback)
  http.get(`${BASE}/activity`, () =>
    HttpResponse.json({ room_key: 'aiml', events: [], count: 0 })
  ),

  // Messages — no SSE in MSW, simulate via response
  http.post(`${BASE}/rooms/:key/messages`, () =>
    HttpResponse.json({ seq: 1, delivered: true, message: 'Mock delivered' }, { status: 201 })
  ),

  // Me project
  http.put(`${BASE}/me/project`, () =>
    HttpResponse.json({ saved: true })
  ),
]
