# NewsOps — project rules

Product: NewsOps is a developer-intelligence tool. A FastAPI + MongoDB backend ingests GitHub, Hacker News, Reddit and RSS, normalises, dedupes, ranks and classifies stories, extracts verbatim install commands and attaches trust badges. A Next.js dashboard shows it. Three Switch agents (Scout, Analyst, Editor) run in Switch Console rooms #aiml, #cloud, #security and call the backend over HTTP. Hackathon deadline: 7 Nov afternoon IST.

Stack: Python 3.11, FastAPI, Motor/MongoDB 7 (mongomock-motor fallback), Pydantic v2, Next.js 14 App Router, TypeScript, Tailwind, TanStack Query, Vitest, Playwright, Docker Compose.

Layout: the repo root IS the Python package `newsops` (relative imports like `from ..core`). Docker copies it to `/app/newsops` with `PYTHONPATH=/app`. Web app is in `web/`.

Hard rules:
- NEVER invent Switch Agent Protocol endpoints, Switch template YAML fields or Console behaviour. The owner (Nikhila) does all Switch Console, template and room work. If something needs Switch knowledge, leave a `TODO(SWITCH-OWNER)` and a working fallback. Do not edit `switch/template.yaml` or `switch/protocol.py`.
- Never claim "verified". Trust badges only: `primary` (API-verified), `vendor_reported`, `community_signal`. Reddit and HN are discovery only.
- Install commands are extracted deterministically and must be a verbatim substring of the README. Never auto-execute. Show source URL and commit SHA.
- Every feature needs an offline/seed path so the demo works with no internet and no API keys. Seeded data is labelled "seeded" in the UI.
- Minimal, local changes. No new frameworks. No rewrites of working modules.
- After each task run `/verify`, then commit (`feat|fix|chore: ...`, one commit per task).
- No secrets and no personal paths (for example `C:\Users\...`) in the repo.
- Only edit files inside your assigned area (see your prompt). If you need a change outside it, write it in your Walkthrough instead of making it.
