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


def handle_response(res: httpx.Response):
    try:
        res.raise_for_status()
        print(json.dumps(res.json(), separators=(",", ":")))
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP Error {res.status_code}: {res.text.strip()}"
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_candidates(args):
    url = f"{API_BASE}/agent/candidates"
    params = {"room": args.room_key, "limit": args.limit}
    try:
        res = httpx.get(url, params=params, headers=get_headers())
        handle_response(res)
    except Exception as e:
        print(f"Connection Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_evidence(args):
    url = f"{API_BASE}/agent/stories/{args.story_id}/evidence"
    try:
        res = httpx.get(url, headers=get_headers())
        handle_response(res)
    except Exception as e:
        print(f"Connection Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_analysis(args):
    try:
        with open(args.file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        url = f"{API_BASE}/agent/stories/{args.story_id}/analysis"
        res = httpx.post(url, json=payload, headers=get_headers())
        handle_response(res)
    except FileNotFoundError:
        print(f"Error: File '{args.file_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in '{args.file_path}'.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_activity(args):
    url = f"{API_BASE}/agent/activity"
    payload = {
        "agent": args.agent,
        "room": args.room,
        "action": args.action,
        "story_id": args.story_id,
        "message": args.message,
    }
    try:
        res = httpx.post(url, json=payload, headers=get_headers())
        handle_response(res)
    except Exception as e:
        print(f"Connection Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_digest(args):
    # Fetch stories for room to curate into a digest
    stories_url = f"{API_BASE}/stories"
    try:
        stories_res = httpx.get(stories_url, params={"topic": args.room_key, "limit": 8}, headers=get_headers())
        stories_res.raise_for_status()
        stories = stories_res.json()
        items = stories.get("items", []) if isinstance(stories, dict) else stories
        story_ids = [s.get("_id") or s.get("id") for s in items if s.get("_id") or s.get("id")]
        if not story_ids:
            # Fallback to candidates
            cand_res = httpx.get(f"{API_BASE}/agent/candidates", params={"room": args.room_key, "limit": 8}, headers=get_headers())
            if cand_res.status_code == 200:
                cands = cand_res.json()
                story_ids = [s.get("_id") or s.get("id") for s in cands if s.get("_id") or s.get("id")]

        if not story_ids:
            print(f"Error: No stories available to build digest for room '{args.room_key}'.", file=sys.stderr)
            sys.exit(1)

        digest_url = f"{API_BASE}/agent/digests"
        res = httpx.post(digest_url, json={"room_key": args.room_key, "story_ids": story_ids}, headers=get_headers())
        handle_response(res)
    except Exception as e:
        print(f"Error creating digest: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_decision(args):
    url = f"{API_BASE}/agent/digests/{args.digest_id}/decision"
    payload = {
        "decision": args.decision,
        "by": args.reviewer,
    }
    try:
        res = httpx.post(url, json=payload, headers=get_headers())
        handle_response(res)
    except Exception as e:
        print(f"Connection Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_publish(args):
    url = f"{API_BASE}/digests/{args.digest_id}/publish"
    try:
        res = httpx.post(url, headers=get_headers())
        if res.status_code == 403:
            print(f"Error 403: Digest '{args.digest_id}' is not in approved status. Cannot publish.", file=sys.stderr)
            sys.exit(1)
        handle_response(res)
    except Exception as e:
        print(f"Connection Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="NewsOps CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # candidates
    p_cand = subparsers.add_parser("candidates", help="Get candidate stories for a room")
    p_cand.add_argument("room_key", help="Room key (e.g. aiml, cloud, security)")
    p_cand.add_argument("--limit", type=int, default=8, help="Max candidates (default: 8)")

    # evidence
    p_ev = subparsers.add_parser("evidence", help="Fetch evidence for a story")
    p_ev.add_argument("story_id", help="Story ID")

    # analysis
    p_an = subparsers.add_parser("analysis", help="Submit analysis file for a story")
    p_an.add_argument("story_id", help="Story ID")
    p_an.add_argument("file_path", help="Path to JSON file containing AnalysisSubmission")

    # activity
    p_act = subparsers.add_parser("activity", help="Record agent activity")
    p_act.add_argument("agent", help="Agent name (e.g. scout, analyst, editor)")
    p_act.add_argument("room", help="Room key (e.g. aiml, cloud, security)")
    p_act.add_argument("action", help="Action name")
    p_act.add_argument("message", help="Activity message")
    p_act.add_argument("--story_id", default=None, help="Optional story ID")

    # digest
    p_dig = subparsers.add_parser("digest", help="Build a draft digest for a room")
    p_dig.add_argument("room_key", help="Room key (e.g. aiml, cloud, security)")

    # decision
    p_dec = subparsers.add_parser("decision", help="Record approval decision for a digest")
    p_dec.add_argument("digest_id", help="Digest ID")
    p_dec.add_argument("decision", choices=["approve", "reject"], help="Decision action")
    p_dec.add_argument("reviewer", help="Chat handle or reviewer name (e.g. @nikhila)")

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
    elif args.command == "activity":
        cmd_activity(args)
    elif args.command == "digest":
        cmd_digest(args)
    elif args.command == "decision":
        cmd_decision(args)
    elif args.command == "publish":
        cmd_publish(args)


if __name__ == "__main__":
    main()
