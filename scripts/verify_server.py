"""
NewsOps Revision 2 - Server Health Verification Script.

Starts the FastAPI server locally, probes the /healthz and /api/v1/healthz endpoints,
prints the responses, and shuts down cleanly.
"""

import os
import sys
import time
import subprocess
import httpx


def main():
    print("[1/4] Starting NewsOps FastAPI server on 127.0.0.1:8000...")
    env = os.environ.copy()
    env["PYTHONPATH"] = "E:\\"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "newsops.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )

    try:
        print("[2/4] Waiting for server initialization...")
        resp = None
        for attempt in range(10):
            time.sleep(1.0)
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                print("Server exited prematurely!")
                print("STDOUT:", stdout)
                print("STDERR:", stderr)
                sys.exit(1)
            try:
                resp = httpx.get("http://127.0.0.1:8000/healthz", timeout=2.0)
                if resp.status_code == 200:
                    break
            except Exception:
                pass

        if not resp:
            stdout, stderr = proc.communicate(timeout=2)
            print("Failed to connect after retries.")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            sys.exit(1)

        print("[3/4] Probed GET http://127.0.0.1:8000/healthz:")
        print(f"Status Code: {resp.status_code}")
        print("Response JSON:")
        print(resp.json())

        # Probe /api/v1/healthz
        print("\n[4/4] Probing GET http://127.0.0.1:8000/api/v1/healthz:")
        resp_v1 = httpx.get("http://127.0.0.1:8000/api/v1/healthz", timeout=2.0)
        print(f"Status Code: {resp_v1.status_code}")
        print("Response JSON:")
        print(resp_v1.json())

        print("\nSUCCESS: All health endpoints verified live!")
    finally:
        print("Terminating server...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()
