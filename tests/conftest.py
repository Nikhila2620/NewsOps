import importlib.util
from pathlib import Path
import sys

# Ensure newsops package is properly loaded when running tests directly
root = Path(__file__).resolve().parent.parent
if "newsops" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "newsops", root / "__init__.py", submodule_search_locations=[str(root)]
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["newsops"] = mod
    spec.loader.exec_module(mod)
