# NewsOps — Frontend (`web/`)

Next.js 14 dashboard companion to the NewsOps FastAPI backend.  
Stack: **Next.js 14 (App Router) · TypeScript (strict) · Tailwind CSS · TanStack Query · MSW (mock mode)**

---

## Install

```bash
cd web
npm install --legacy-peer-deps
```

---

## Environment variables

Copy the example and fill in:

```bash
cp .env.example .env.local
```

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000/api/v1` | Backend API URL |
| `NEXT_PUBLIC_MATTERMOST_URL` | _(empty)_ | Adds "Open in Mattermost" link when set |
| `NEXT_PUBLIC_MOCK` | _(empty)_ | Set to `1` to run in mock mode (no backend needed) |

---

## Run with the backend

1. Start the backend (from the project root):
   ```bash
   pip install fastapi uvicorn pydantic pydantic-settings motor pymongo mongomock-motor httpx
   uvicorn newsops.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. Start the frontend:
   ```bash
   cd web
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000).

---

## Run in mock mode (no backend required)

```bash
NEXT_PUBLIC_MOCK=1 npm run dev
```

All API calls are intercepted by [MSW](https://mswjs.io/).  
The mock reproduces the demo sequence: send `@scout aiml last 24h` in the room panel
to watch the Scout → Analyst → Editor pipeline play out with sample data.

---

## Run with Docker Compose

From the project root:

```bash
cp .env.example .env          # configure secrets
docker compose up --build
```

- Backend: [http://localhost:8000](http://localhost:8000)  
- Frontend: [http://localhost:3000](http://localhost:3000)  
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Type generation

```bash
npm run gen:api
```

Generates `src/api/schema.d.ts` from the backend's OpenAPI spec.  
Requires the backend to be running.

---

## Unit tests

```bash
npm test
```

Tests (11 passing):
- `helpers.test.ts` — message HTML escaping, **bold** / `code` formatting, @mentions
- SSE seq de-duplication reducer
- Impact severity label and confidence display helpers

---

## Screens

| Route | Description |
|---|---|
| `/` | Inbox — pipeline card, story cards with trust badges, story detail drawer |
| `/radar` | SVG tech radar — blip placement, voting, ring animation |
| `/dependencies` | Dependency impact scanner — requirements.txt / package.json |
| `/review` | Human approval — gate bar, approve/reject/publish, audit trail |

---

## API mismatches worked around

| Issue | Resolution |
|---|---|
| Backend had no `POST /auth/demo-login` | Added in `api/auth.py` — issues demo tokens for Alice / Sam |
| No SSE event feed (`GET /events`) | Added in `api/events.py` with in-memory pub/sub |
| No `GET /activity` replay endpoint | Added in `api/events.py` |
| No `GET /rooms/{key}/state` | Added in `api/events.py` |
| No `POST /rooms/{key}/messages` | Added in `api/events.py` |
| No `POST /demo/reset` | Added in `api/demo.py` |
| No `POST /impact/scan` / `PUT /me/project` | Added in `api/impact.py` |
| No `PATCH /digests/{id}/items/{story_id}` | Added to `api/digests.py` |
