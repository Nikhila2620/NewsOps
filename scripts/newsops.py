#!/usr/bin/env python3
"""
NewsOps CLI Wrapper.

Provides command-line interface for human operators and Switch agents.
Reads NEWSOPS_API and AGENT_API_TOKEN from environment.
"""

import argparse
import json
import os
import sys
import httpx

API_BASE = os.getenv("NEWSOPS_API", "http://localhost:8000/api/v1").rstrip("/")
TOKEN = os.getenv("AGENT_API_TOKEN", "dev-agent-secret-token-change-me")


def get_headers():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }


def cmd_candidates(args):
    url = f"{API_BASE}/stories"
    params = {"topic": args.room_key} if args.room_key else {}
    res = httpx.get(url, params=params, headers=get_headers())
    res.raise_for_status()
    print(json.dumps(res.json(), indent=2))


def cmd_evidence(args):
    url = f"{API_BASE}/stories/{args.story_id}"
    res = httpx.get(url, headers=get_headers())
    res.raise_for_status()
    story = res.json()
    print(json.dumps({"story_id": args.story_id, "evidence": story.get("evidence", [])}, indent=2))


def cmd_analysis(args):
    with open(args.file_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    url = f"{API_BASE}/agent/stories/{args.story_id}/analysis"
    res = httpx.post(url, json=payload, headers=get_headers())
    res.raise_for_status()
    print(json.dumps(res.json(), indent=2))


def cmd_decision(args):
    url = f"{API_BASE}/digests/{args.digest_id}/{args.action}"
    payload = {"comment": f"Decided by {args.reviewer}"}
    res = httpx.post(url, json=payload, headers=get_headers())
    res.raise_for_status()
    print(json.dumps(res.json(), indent=2))


def cmd_publish(args):
    url = f"{API_BASE}/digests/{args.digest_id}/publish"
    res = httpx.post(url, headers=get_headers())
    if res.status_code == 403:
        print(f"Error 403: Digest '{args.digest_id}' is not in approved status. Cannot publish.")
        sys.exit(1)
    res.raise_for_status()
    print(json.dumps(res.json(), indent=2))


def main():
    parser = argparse.ArgumentParser(description="NewsOps CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # candidates
    p_cand = subparsers.add_parser("candidates", help="Get candidate stories for a room")
    p_cand.add_argument("room_key", help="Room key (e.g. aiml, cloud, security)")

    # evidence
    p_ev = subparsers.add_parser("evidence", help="Fetch evidence for a story")
    p_ev.add_argument("story_id", help="Story ID")

    # analysis
    p_an = subparsers.add_parser("analysis", help="Submit analysis file for a story")
    p_an.add_argument("story_id", help="Story ID")
    p_an.add_argument("file_path", help="Path to JSON file containing AnalysisSubmission")

    # decision
    p_dec = subparsers.add_parser("decision", help="Record approval decision for a digest")
    p_dec.add_argument("digest_id", help="Digest ID")
    p_dec.add_argument("action", choices=["approve", "reject", "request-changes"], help="Decision action")
    p_dec.add_argument("reviewer", help="Chat handle or reviewer name")

    # publish
    p_pub = subparsers.add_parser("publish", help="Publish approved digest")
    p_pub.add_argument("digest_id", help="Digest ID")

    args = parser.parse_args()
    if args.command == "candidates":
        cmd_candidates(args)
    elif args.command == "evidence":
        cmd_evidence(args)
    elif args.command == "analysis":
        cmd_analysis(args)
    elif args.command == "decision":
        cmd_decision(args)
    elif args.command == "publish":
        cmd_publish(args)


if __name__ == "__main__":
    main()
