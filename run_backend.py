#!/usr/bin/env python3
"""
NewsOps Local Backend Runner.
Ensures 'newsops' package resolves correctly and starts Uvicorn.
"""
import sys
from pathlib import Path
import importlib.util

root = Path(__file__).resolve().parent
if "newsops" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "newsops", root / "__init__.py", submodule_search_locations=[str(root)]
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["newsops"] = mod
    spec.loader.exec_module(mod)

import uvicorn
from newsops.config.settings import settings

if __name__ == "__main__":
    print(f"[*] Starting NewsOps API server on http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"[*] OpenAPI Docs available at http://localhost:{settings.API_PORT}/docs")
    uvicorn.run("newsops.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=False)
