---
description: Run all verification checks for NewsOps
---

1. From the parent directory of the repo (or root with PYTHONPATH=.), run:
   ```bash
   python -m pytest tests -q
   ```
2. Run frontend type check and test:
   ```bash
   cd web && npm run type-check && npm test
   ```
3. If any step fails, fix the cause and rerun. Do not weaken or delete tests.
4. Print a 2-line summary: tests passed/failed counts, and any TODO(SWITCH-OWNER) added.
