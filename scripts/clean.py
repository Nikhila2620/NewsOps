"""
NewsOps - Project Workspace Cleaner.

Cross-platform utility to strip temporary files, bytecode, build output,
and caches without deleting virtualenvs or node_modules.

Usage:
    python scripts/clean.py
"""

import shutil
from pathlib import Path


def clean_workspace():
    root = Path(__file__).resolve().parent.parent
    freed_bytes = 0

    # Folders to completely remove
    dir_names_to_remove = ["__pycache__", ".pytest_cache", ".next", ".turbo", "out", "build", "dist"]

    print(f"[*] Cleaning workspace at: {root}")

    for path in root.rglob("*"):
        if "node_modules" in path.parts or ".git" in path.parts:
            continue

        if path.is_dir() and path.name in dir_names_to_remove:
            size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            try:
                shutil.rmtree(path)
                freed_bytes += size
                print(f"  [-] Removed directory: {path.relative_to(root)} ({size / 1024:.1f} KB)")
            except Exception as e:
                print(f"  [!] Failed to remove {path}: {e}")

    # Files to remove
    file_extensions_to_remove = [".pyc", ".pyo", ".tsbuildinfo"]
    for path in root.rglob("*"):
        if "node_modules" in path.parts or ".git" in path.parts:
            continue

        if path.is_file():
            if path.suffix in file_extensions_to_remove or path.name.endswith(".zip"):
                size = path.stat().st_size
                try:
                    path.unlink()
                    freed_bytes += size
                    print(f"  [-] Removed file: {path.relative_to(root)} ({size / 1024:.1f} KB)")
                except Exception as e:
                    print(f"  [!] Failed to remove {path}: {e}")

    print(f"[+] Done! Freed {freed_bytes / (1024 * 1024):.2f} MB of temporary artifacts.")


if __name__ == "__main__":
    clean_workspace()
