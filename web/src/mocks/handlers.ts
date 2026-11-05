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
    id: 'story-mock-001',
    title: 'vLLM v0.6.4: Speculative Decoding & Chunked Prefill Acceleration',
    summary: 'The vLLM release introduces hardware-optimized speculative decoding reducing TTFT by 32% for Llama 3 models.',
    source_domain: 'github.com',
    source_url: 'https://github.com/vllm-project/vllm/releases/tag/v0.6.4',
    published_at: new Date(Date.now() - 3600000).toISOString(),
    room_key: 'aiml',
    topics: ['aiml', 'llm'],
    trust_badge: 'primary',
    badge: 'primary',
    confidence: 0.95,
    risk_flags: [],
    install_command: 'pip install vllm>=0.6.4',
    install_commit: 'a1b2c3d4e5f67890abcdef1234567890abcdef12',
    commit_sha: 'a1b2c3d4e5f67890abcdef1234567890abcdef12',
    seeded: true,
    claims: [
      { text: 'vLLM v0.6.4 supports multi-step speculative decoding', status: 'supported', evidence_note: 'Confirmed in release notes' },
      { text: 'Chunked prefill is enabled by default in v0.6.4', status: 'supported', evidence_note: 'Upstream documentation' },
    ],
    evidence: [
      { evidence_url: 'https://github.com/vllm-project/vllm/releases/tag/v0.6.4', evidence_type: 'primary_source', source_reference: 'GitHub Release Tag v0.6.4', status: 'supported', confidence: 0.98 },
    ],
    analysis: {
      summary: 'vLLM v0.6.4 delivers massive speculative decoding latency benefits.',
      why_it_matters: 'Decreases inference cost and latency for LLM serving architectures.',
      confidence: 0.95,
    },
  },
  {
    _id: 'story-mock-002',
    id: 'story-mock-002',
    title: 'CRITICAL: requests library SSRF via redirect following (CVE-2024-1234)',
    summary: 'A server-side request forgery vulnerability allows proxy-authorization header leakage on redirects.',
    source_domain: 'github.com',
    source_url: 'https://osv.dev/vulnerability/GHSA-4412-pytorch',
    published_at: new Date(Date.now() - 7200000).toISOString(),
    room_key: 'security',
    topics: ['security', 'cve'],
    trust_badge: 'primary',
    badge: 'primary',
    confidence: 0.97,
    risk_flags: ['CVE', 'SSRF', 'HIGH'],
    impact: 'Any service using requests with proxy auth is potentially affected',
    install_command: 'pip install "requests>=2.31.0"',
    install_commit: 'b2c3d4e5f6a17890abcdef1234567890abcdef12',
    commit_sha: 'b2c3d4e5f6a17890abcdef1234567890abcdef12',
    seeded: true,
    claims: [
      { text: 'Proxy-Authorization header leaks on 301 redirects', status: 'supported', evidence_note: 'CVE database entry' },
    ],
    evidence: [
      { evidence_url: 'https://osv.dev', evidence_type: 'primary_source', source_reference: 'OSV API', status: 'supported', confidence: 0.99 },
    ],
  },
  {
    _id: 'story-mock-003',
    id: 'story-mock-003',
    title: 'Kubernetes 1.32 promotes Gateway API to stable GA',
    summary: 'Gateway API v1.2 HTTPRoute and GRPCRoute are now generally available natively.',
    source_domain: 'kubernetes.io',
    source_url: 'https://kubernetes.io',
    published_at: new Date(Date.now() - 86400000).toISOString(),
    room_key: 'cloud',
    topics: ['cloud', 'infrastructure'],
    trust_badge: 'vendor_reported',
    badge: 'vendor_reported',
    confidence: 0.88,
    risk_flags: [],
    install_command: 'kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml',
    install_commit: 'c3d4e5f6a1b27890abcdef1234567890abcdef12',
    commit_sha: 'c3d4e5f6a1b27890abcdef1234567890abcdef12',
    seeded: true,
    claims: [
      { text: 'Gateway API v1.2 is generally available', status: 'supported', evidence_note: 'Kubernetes official blog' },
    ],
    evidence: [
      { evidence_url: 'https://kubernetes.io/blog', evidence_type: 'primary_source', source_reference: 'Official Blog', status: 'supported', confidence: 0.95 },
    ],
  },
]

const RADAR_ITEMS = [
  { _id: 'radar-001', name: 'vLLM', room_key: 'aiml', ring: 'adopt', description: 'High-throughput LLM inference engine', votes: { adopt: 18, trial: 2, assess: 1, hold: 0 }, user_vote: null },
  { _id: 'radar-002', name: 'Kubernetes Gateway API', room_key: 'cloud', ring: 'adopt', description: 'Next-gen cloud native ingress', votes: { adopt: 12, trial: 3, assess: 1, hold: 0 }, user_vote: null },
  { _id: 'radar-003', name: 'TruffleHog', room_key: 'security', ring: 'adopt', description: 'Zero-false-positive secret detection', votes: { adopt: 22, trial: 4, assess: 1, hold: 0 }, user_vote: null },
]

let _radarItems: any[] = RADAR_ITEMS.map(i => ({ ...i }))

let _activities = [
  { _id: 'act-1', id: 'act-1', agent: 'scout', room: 'aiml', action: 'candidate_discovery', message: 'Discovered 4 new candidate releases', created_at: new Date(Date.now() - 60000).toISOString() },
  { _id: 'act-2', id: 'act-2', agent: 'analyst', room: 'aiml', action: 'claim_verification', message: 'Verified vLLM v0.6.4 speculative decoding claims', created_at: new Date(Date.now() - 30000).toISOString() },
  { _id: 'act-3', id: 'act-3', agent: 'editor', room: 'aiml', action: 'digest_compilation', message: 'Compiled weekly AI/ML Intelligence digest', created_at: new Date(Date.now() - 10000).toISOString() },
]

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
  http.get(`${BASE}/stories/:id`, ({ params }) => {
    const found = STORIES.find(s => s._id === params.id || s.id === params.id)
    if (found) return HttpResponse.json(found)
    return HttpResponse.json(STORIES[0])
  }),
  http.post(`${BASE}/stories/:id/feedback`, async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ status: 'accepted', feedback: body })
  }),
  http.post(`${BASE}/stories/:id/repost`, async ({ request }) => {
    const body = await request.json() as { room_key: string }
    return HttpResponse.json({ status: 'reposted', room_key: body.room_key })
  }),

  // Agent API
  http.get(`${BASE}/agent/activity`, ({ request }) => {
    const url = new URL(request.url)
    const room = url.searchParams.get('room')
    if (room) {
      return HttpResponse.json(_activities.filter(a => a.room === room))
    }
    return HttpResponse.json(_activities)
  }),
  http.post(`${BASE}/agent/activity`, async ({ request }) => {
    const body = await request.json() as any
    const newAct = {
      _id: `act-${Date.now()}`,
      id: `act-${Date.now()}`,
      agent: body.agent,
      room: body.room,
      action: body.action,
      message: body.message,
      created_at: new Date().toISOString(),
    }
    _activities.unshift(newAct)
    return HttpResponse.json(newAct, { status: 201 })
  }),
  http.get(`${BASE}/agent/candidates`, () => HttpResponse.json(STORIES)),

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

  // Rooms
  http.get(`${BASE}/rooms`, () => HttpResponse.json([
    { _id: 'room-aiml-001', key: 'aiml', name: 'AI/ML Intelligence', topics: ['aiml', 'llm'],
      approvers: ['alice_aiml', 'lead_reviewer'], chat_channel_id: 'channel-aiml', members: [{ user_id: 'user-001', role: 'admin' }] },
    { _id: 'room-cloud-002', key: 'cloud', name: 'Cloud & Platform Eng', topics: ['cloud', 'devtools'],
      approvers: ['bob_cloud', 'lead_reviewer'], chat_channel_id: 'channel-cloud', members: [{ user_id: 'user-002', role: 'admin' }] },
    { _id: 'room-sec-003', key: 'security', name: 'Security & Supply Chain', topics: ['security', 'cve'],
      approvers: ['lead_reviewer'], chat_channel_id: 'channel-security', members: [{ user_id: 'user-003', role: 'admin' }] },
  ])),
  http.get(`${BASE}/rooms/:key/state`, ({ params }) =>
    HttpResponse.json({ room_key: params.key, room_name: params.key, step: -1,
                        status: 'idle', agents: ['scout','analyst','editor'],
                        approvers: ['alice_aiml', 'lead_reviewer'], chat_channel_id: '', digest: null, last_seq: 0 })
  ),
  http.post(`${BASE}/rooms/:key/invites`, async ({ params, request }) => {
    const body = await request.json() as any
    return HttpResponse.json({ _id: `inv-${Date.now()}`, room_key: params.key, invitee_handle: body.invitee_handle, status: 'pending' }, { status: 201 })
  }),
  http.get(`${BASE}/invites`, () => HttpResponse.json([])),

  // Digests
  http.get(`${BASE}/digests`, () => HttpResponse.json([])),

  // Switch status
  http.get(`${BASE}/switch/status`, () =>
    HttpResponse.json({ mode: 'cli_agent_dispatch', message: 'agents call NewsOps via CLI; last agent activity at recently' })
  ),

  // Demo reset
  http.post(`${BASE}/demo/reset`, () =>
    HttpResponse.json({ reset: true, message: 'Mock reset.' })
  ),
]
