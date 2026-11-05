# NewsOps × Switch — Developer Intelligence Engine (Revision 2)

NewsOps is a full-stack, AI-powered developer intelligence and fact-checking platform built for the **Flip the Switch Hackathon (4–7 Nov 2026)**.

NewsOps monitors technical ecosystems across GitHub, Hacker News, Reddit, and RSS feeds, automatically normalizes and deduplicates articles, extracts install commands and security advisories, performs rigorous claim extraction and evidence-backed verification ("The No Fake News Layer"), and prepares human-in-the-loop digests delivered via the **Switch Agent Protocol**.

---

## 1. Complete Architecture

```
newsops/
├── ai/                           # AI & Verification Engine ("The No Fake News Layer")
│   ├── analyst.py                # Narrative synthesis, claim verification & submission generator
│   ├── claim_extractor.py        # Atomic verifiable claim extractor (VERSION, SECURITY, BENCHMARK...)
│   ├── classifier.py             # Topic classification with confidence scoring
│   ├── evidence_evaluator.py     # Multi-tier evidence evaluation & contradiction detection
│   └── prompt_guard.py           # Prompt injection detection, sanitization & jailbreak shielding
├── api/                          # FastAPI REST API Layer (NewsOps Revision 2 §9)
│   ├── agent_analysis.py         # POST /api/v1/agent/stories/{id}/analysis (analyst submission)
│   ├── deps.py                   # Identity & chat-handle dependency resolution
│   ├── digests.py                # GET/POST /digests, /approve, /reject, /publish (403 Publish Gate)
│   ├── health.py                 # Health-check endpoints (/healthz, /api/v1/healthz)
│   ├── invites.py                # Room invitations workflow (/rooms/{key}/invites, /invites)
│   ├── me.py                     # Profile and user preferences (/me, /me/profile)
│   ├── radar.py                  # Community radar submissions & unique voting (/radar)
│   ├── rooms.py                  # Topic room management (/rooms, /members, /agents)
│   ├── router.py                 # Central v1 route aggregator
│   ├── sources.py                # Connector registry & source health (/sources)
│   ├── stories.py                # Clustered story catalog & feedback (/stories)
│   ├── switch_status.py          # Switch Agent Protocol connection transparency (/switch/status)
│   └── tasks.py                  # Ingestion & ranking task orchestration (/tasks)
├── config/                       # Settings & Environment Validation
│   └── settings.py               # Pydantic Settings v2 with strict bounds & masked credentials
├── connectors/                   # Multi-Source Ingestion Connectors (Spec §7.1)
│   ├── base.py                   # SourceConnector Protocol & ConnectorUnavailableError
│   ├── github.py                 # GitHub REST API (README install command extraction & risk flags)
│   ├── hackernews.py             # Algolia Hacker News Search API (zero credentials required)
│   ├── reddit.py                 # Reddit OAuth API with graceful credential-fallback
│   └── rss.py                    # RSS & Atom developer feed parser
├── contracts/                    # Member 2 Shared Pydantic v2 JSON Contracts & Enums
│   ├── analysis.py               # StoryAnalysis schema
│   ├── claim.py                  # Claim schema
│   ├── enums.py                  # Exact EvidenceType, EvidenceStatus, ClaimType, TrustBadgeKind
│   ├── evidence.py               # Evidence schema (with community_signal rules)
│   ├── submission.py             # AnalysisSubmission schema
│   └── verification.py           # VerificationResult schema with auto-escalation
├── core/                         # Cross-Cutting Infrastructure
│   ├── errors.py                 # Centralized { "error": { "code", "message", "task_id" } }
│   └── logging.py                # Structured JSON logging with automated secret redaction
├── db/                           # Persistence Layer (MongoDB 7)
│   ├── indexes.py                # Idempotent index creation matching Revision 2 §6
│   ├── mongodb.py                # Motor async MongoDB client with resilient mock fallback
│   └── seed.py                   # Initial seed data for #aiml, #cloud, #security rooms & users
├── eval/                         # AI Evaluation Benchmark
│   └── dataset.py                # 20 hand-labeled samples & metrics calculation (95% accuracy)
├── fixtures/                     # Standard JSON Fixtures (7 examples)
├── models/                       # Domain Models & MongoDB Document Schemas
│   ├── digest.py                 # Digest, DigestItem, DigestStatus, ApprovalRecord
│   ├── invite.py                 # RoomInvite, InviteCreate, InviteStatus
│   ├── room.py                   # Room, RoomCreate, RoomMember, RoomRules
│   ├── source.py                 # Source document
│   ├── story.py                  # Story, ClusterMember, StoryFeedback
│   ├── task.py                   # Task, TaskCreate, TaskStatus
│   └── user.py                   # User, UserProfileUpdate
├── pipeline/                     # Data Processing & Normalization Pipeline
│   ├── classify.py               # Keyword taxonomy mapping (aiml, cloud, security, etc.)
│   ├── commands.py               # Verbatim install command extraction & risk flag detection
│   ├── dedupe.py                 # Exact URL, content-hash, and fuzzy similarity deduplication
│   ├── normalize.py              # URL canonicalization & content_hash SHA-256 computation
│   └── rank.py                   # Multi-variable relevance ranking (0.35*rel + 0.25*src + 0.20*rec...)
├── scripts/                      # Developer Utilities & CLI
│   ├── newsops.py                # Operator & agent CLI wrapper
│   └── verify_server.py          # Server lifecycle probe & health validator
├── switch/                       # Live Switch Agent Protocol Integration
│   ├── agents/                   # Autonomous Agents
│   │   ├── scout.py              # News discovery & candidate collection
│   │   ├── analyst.py            # Claim verification & evidence evaluation
│   │   └── editor.py             # Digest compilation & approval-gated publishing
│   ├── protocol.py               # HTTP operations & event client
│   └── template.yaml             # Switch platform room & agent manifest
├── tests/                        # 70 Comprehensive Pytest Tests (100% Passing)
├── .env.example                  # Environment configuration template
└── main.py                       # FastAPI application entrypoint with lifespan
```

---

## 2. Setup & Installation

### 2.1 Prerequisites
- Python 3.10+ (tested on Python 3.15)
- MongoDB 7 (optional; automatic in-memory mock database is included for tests and development)

### 2.2 Installation
```bash
# Clone and enter directory
cd newsops

# Install required dependencies
pip install fastapi uvicorn pydantic pydantic-settings motor pymongo mongomock-motor httpx pytest anyio
```

### 2.3 Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key variables:
- `MONGODB_URI`: Connection string (defaults to `mongodb://localhost:27017`; automatically falls back to `mongomock-motor` if MongoDB is offline).
- `AGENT_API_TOKEN`: Secret token used by Switch template agents for `/api/v1/agent/*`.
- `SWITCH_BASE_URL`: Base URL for Switch platform (optional for live runtime).
- `SWITCH_POSTER_TOKEN`: Auth token for Switch agent messaging.

---

## 3. Running the Server

### Start FastAPI Server
```bash
python -m uvicorn newsops.main:app --host 0.0.0.0 --port 8000 --reload
```

### Verify Server Health Live
```bash
python newsops/scripts/verify_server.py
```
Outputs:
```json
{
  "status": "ok",
  "service": "NewsOps",
  "environment": "dev",
  "database": {
    "status": "connected",
    "database": "newsops",
    "is_mock": true,
    "engine": "mongomock-motor"
  },
  "version": "2.0.0-rev2"
}
```

---

## 4. Part 3 — Connect Switch Docs MCP to Antigravity

Antigravity uses the standard Model Context Protocol (MCP) Streamable HTTP transport to connect with documentation servers.

### Configuration Location
Open `C:\Users\ESHWAR\.gemini\config\mcp_config.json` (or `~/.gemini/config/mcp_config.json`).

### Add the Switch Docs MCP Server
Add the `switch-docs` server entry:
```json
{
  "mcpServers": {
    "switch-docs": {
      "url": "https://docs.switchagents.ai/mcp"
    }
  }
}
```
*Note: Existing MCP servers in `mcp_config.json` are preserved. The IDE automatically discovers tools and prompts exposed by the Switch documentation endpoint.*

---

## 5. Part 4 — Switch Agent Protocol Implementation

NewsOps implements three autonomous agents coordinating via the Switch Agent Protocol:

1. **SCOUT (`newsops.switch.agents.scout.ScoutAgent`)**:
   - Queries `GET /api/v1/stories` for new candidate stories across rooms.
   - Enqueues ingestion tasks via `POST /api/v1/tasks`.
   - Posts discovery briefings to Switch topic rooms.
   - Hands off story candidates to the **Analyst**.

2. **ANALYST (`newsops.switch.agents.analyst.AnalystSwitchAgent`)**:
   - Fetches story details and source artifacts.
   - Sanitizes untrusted content with `PromptGuard`.
   - Extracts atomic claims (`VERSION`, `SECURITY`, `BENCHMARK`, `CAPABILITY`).
   - Cross-checks claims against multi-tier evidence (`PRIMARY_SOURCE`, `INDEPENDENT_REPORTING`, `COMMUNITY_SIGNAL`).
   - Disallows `COMMUNITY_SIGNAL` alone from verifying a claim as `SUPPORTED`.
   - Auto-escalates stories to `review_required` if confidence < 0.70 or contradictions exist.
   - Posts structured evaluation to `POST /api/v1/agent/stories/{id}/analysis`.

3. **EDITOR (`newsops.switch.agents.editor.EditorAgent`)**:
   - Assembles verified candidate stories into curated digests (`GET /api/v1/digests`).
   - **Enforces the Non-Negotiable Publish Gate**: Publication via `POST /api/v1/digests/{id}/publish` returns **HTTP 403 Forbidden** unless the digest has been approved by an authorized room reviewer.

---

## 6. NewsOps CLI

The `scripts/newsops.py` CLI provides command-line control for human operators and Switch agents:

```bash
# 1. Fetch candidate stories for room
python newsops/scripts/newsops.py candidates aiml

# 2. Inspect evidence for a story
python newsops/scripts/newsops.py evidence <story_id>

# 3. Submit analysis payload
python newsops/scripts/newsops.py analysis <story_id> fixtures/example_analysis_submission.json

# 4. Record human approval decision
python newsops/scripts/newsops.py decision <digest_id> approve "@alice"

# 5. Publish approved digest (returns 403 if unapproved)
python newsops/scripts/newsops.py publish <digest_id>
```

---

## 7. Running Tests & Benchmarks

### Complete Pytest Suite (70 Tests)
```bash
python -m pytest newsops/tests -v
```
All **70 tests** pass:
- `test_contracts.py` (21 tests) — Evidence & verification contracts, bounds, validation rules
- `test_fixtures.py` (7 tests) — Schema alignment of all sample fixtures
- `test_api.py` (8 tests) — FastAPI routes, error responses, authentication
- `test_models.py` (5 tests) — Domain models & MongoDB schemas
- `test_pipeline.py` (13 tests) — Deduplication, ranking, canonicalization, command extraction
- `test_ai.py` (6 tests) — Prompt injection defense, claim extraction, evidence evaluation
- `test_connectors.py` (3 tests) — SourceConnector protocols & graceful fallbacks
- `test_switch.py` (4 tests) — Scout, Analyst, Editor agents and protocol client
- `test_digest_approval.py` (3 tests) — 403 publish gate & approval transitions

### AI Evaluation Benchmark
```bash
python -m newsops.eval.dataset
```
Benchmark Results:
- **Total Samples**: 20 hand-labeled technical announcements
- **Topic Accuracy**: 95.0%
- **Vulnerability Precision**: 75.0%
- **Vulnerability Recall**: 60.0%
- **Vulnerability F1 Score**: 0.6667
