#!/usr/bin/env python3
"""
NewsOps End-to-End Smoke Test.

Validates the full agent lifecycle against a running NewsOps instance:
1. Candidates retrieval (Scout)
2. Evidence & verbatim install commands retrieval (Analyst)
3. Schema-validated Analysis submission (Analyst)
4. Draft Digest compilation (Editor)
5. 403 Publish Gate verification (Security Gate)
6. Digest approval by authorized room approver
7. Publication of approved digest

Reads NEWSOPS_API and AGENT_API_TOKEN from environment.
Exits 0 on complete pass, 1 on any failure.
"""

import os
import sys
import uuid
import httpx

API_BASE = os.getenv("NEWSOPS_API", "http://localhost:8000/api/v1").rstrip("/")
TOKEN = os.getenv("AGENT_API_TOKEN", "dev-agent-secret-token-change-me")


def get_headers():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }


def run_smoke():
    client = httpx.Client(timeout=10.0)
    print("=" * 60)
    print("           NewsOps End-to-End Smoke Test")
    print(f" Target API: {API_BASE}")
    print("=" * 60)

    # 1. Check health
    try:
        health_res = client.get(f"{API_BASE}/healthz")
        health_res.raise_for_status()
        print("[-] Target API is healthy.")
    except Exception as e:
        print(f"[FAIL] Health check failed at {API_BASE}/healthz: {e}")
        sys.exit(1)

    # Step 1: Candidates
    step1_url = f"{API_BASE}/agent/candidates?room=aiml&limit=8"
    try:
        r1 = client.get(step1_url, headers=get_headers())
        r1.raise_for_status()
        candidates = r1.json()
        if not candidates:
            # Fallback check regular stories
            r_all = client.get(f"{API_BASE}/stories?limit=8", headers=get_headers())
            candidates = r_all.json().get("items", [])
        if not candidates:
            print("[FAIL] Step 1 Candidates: No candidates or stories returned.")
            sys.exit(1)
        story = candidates[0]
        story_id = story.get("_id") or story.get("id")
        print(f"[PASS] Step 1 Candidates: Retrieved {len(candidates)} stories. Selected: {story_id}")
    except Exception as e:
        print(f"[FAIL] Step 1 Candidates: {e}")
        sys.exit(1)

    # Step 2: Evidence
    step2_url = f"{API_BASE}/agent/stories/{story_id}/evidence"
    try:
        r2 = client.get(step2_url, headers=get_headers())
        r2.raise_for_status()
        evidence_data = r2.json()
        print(f"[PASS] Step 2 Evidence: Retrieved evidence for '{story_id}' (Title: {evidence_data.get('title')[:40]}...)")
    except Exception as e:
        print(f"[FAIL] Step 2 Evidence: {e}")
        sys.exit(1)

    # Step 3: Analysis
    step3_url = f"{API_BASE}/agent/stories/{story_id}/analysis"
    fixture_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures", "example_analysis_submission.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        submission_payload = json.load(f)
    submission_payload["story_id"] = story_id
    try:
        r3 = client.post(step3_url, json=submission_payload, headers=get_headers())
        r3.raise_for_status()
        print(f"[PASS] Step 3 Analysis: Successfully submitted analysis for '{story_id}'.")
    except Exception as e:
        print(f"[FAIL] Step 3 Analysis: {e}")
        sys.exit(1)

    # Step 4: Digest
    step4_url = f"{API_BASE}/agent/digests"
    try:
        r4 = client.post(step4_url, json={"room_key": "aiml", "story_ids": [story_id]}, headers=get_headers())
        r4.raise_for_status()
        digest = r4.json()
        digest_id = digest.get("_id") or digest.get("id")
        print(f"[PASS] Step 4 Digest Creation: Created draft digest '{digest_id}' with status '{digest.get('status')}'.")
    except Exception as e:
        print(f"[FAIL] Step 4 Digest: {e}")
        sys.exit(1)

    # Step 5: Publish Gate (must be 403 before approval)
    publish_url = f"{API_BASE}/digests/{digest_id}/publish"
    try:
        r5 = client.post(publish_url, headers=get_headers())
        if r5.status_code == 403:
            print(f"[PASS] Step 5 Publish Gate: HTTP 403 Forbidden verified on unapproved digest.")
        else:
            print(f"[FAIL] Step 5 Publish Gate: Expected 403, got {r5.status_code}.")
            sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Step 5 Publish Gate: {e}")
        sys.exit(1)

    # Step 6: Decision / Approval by authorized approver
    decision_url = f"{API_BASE}/agent/digests/{digest_id}/decision"
    try:
        # First verify non-approver gets 403
        r_unauth = client.post(decision_url, json={"decision": "approve", "by": "unauthorized_user"}, headers=get_headers())
        if r_unauth.status_code != 403:
            print(f"[FAIL] Step 6 Approver Check: Expected 403 for unauthorized user, got {r_unauth.status_code}")
            sys.exit(1)

        # Authorized approver
        r6 = client.post(decision_url, json={"decision": "approve", "by": "lead_reviewer"}, headers=get_headers())
        r6.raise_for_status()
        app_digest = r6.json()
        print(f"[PASS] Step 6 Digest Decision: Approved by 'lead_reviewer'. Status is '{app_digest.get('status')}'.")
    except Exception as e:
        print(f"[FAIL] Step 6 Digest Decision: {e}")
        sys.exit(1)

    # Step 7: Publish approved digest
    try:
        r7 = client.post(publish_url, headers=get_headers())
        r7.raise_for_status()
        pub_digest = r7.json()
        print(f"[PASS] Step 7 Publish: Digest '{digest_id}' successfully published! Status: '{pub_digest.get('status')}'.")
    except Exception as e:
        print(f"[FAIL] Step 7 Publish: {e}")
        sys.exit(1)

    print("=" * 60)
    print("        ALL 7 SMOKE TEST STEPS PASSED SUCCESSFULLY")
    print("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    run_smoke()
