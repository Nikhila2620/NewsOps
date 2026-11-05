---
description: Run all checks for NewsOps
---
1. From the parent directory of the repo (so the package imports as `newsops`), run: python -m pytest newsops/tests -q
2. cd web && npm run type-check && npm test
3. If any step fails, fix the cause and rerun. Do not weaken or delete tests.
4. Print a 2-line summary: tests passed/failed counts, and any TODO(SWITCH-OWNER) added.
