"""
NewsOps Revision 2 - Analyst Agent Engine.

Wraps claim extraction, prompt injection filtering, and evidence evaluation.
Produces AnalysisSubmission for POST /agent/stories/{id}/analysis.
"""

from datetime import datetime, timezone
from typing import List, Optional
import httpx

from ..contracts.analysis import StoryAnalysis
from ..contracts.enums import AnalysisStatus
from ..contracts.evidence import Evidence
from ..contracts.submission import AnalysisSubmission
from .claim_extractor import extract_claims
from .evidence_evaluator import evaluate_story
from .prompt_guard import guard_input
from ..pipeline.classify import classify_topics


class AnalystAgent:
    """
    Analyst agent responsible for:
    1. Neutralizing prompt injections in raw content
    2. Classifying topics
    3. Extracting verifiable claims
    4. Evaluating evidence
    5. Generating structured AnalysisSubmission
    """

    def analyze_story(
        self,
        story_id: str,
        title: str,
        text: str,
        evidence_pool: Optional[List[Evidence]] = None,
        trust_tier: int = 2,
        analyst_id: str = "analyst-agent",
    ) -> AnalysisSubmission:
        evidence_pool = evidence_pool or []

        # 1. Guard against prompt injection
        guarded_title = guard_input(title, "story_title")
        guarded_text = guard_input(text, "story_text")

        clean_title = guarded_title["clean"]
        clean_text = guarded_text["clean"]

        # 2. Classify topics
        topics, topic_confidence = classify_topics(clean_title, clean_text)

        # 3. Extract atomic claims
        claims = extract_claims(clean_title, clean_text, story_id)

        # 4. Evaluate evidence for each claim
        verification_results = evaluate_story(story_id, claims, evidence_pool, trust_tier)

        # 5. Compute overall confidence
        if verification_results:
            avg_conf = sum(r.confidence for r in verification_results) / len(verification_results)
        else:
            avg_conf = 0.35

        overall_confidence = round(min(avg_conf, topic_confidence * 0.4 + avg_conf * 0.6), 3)

        # 6. Build narrative summary
        injection_notes = []
        if guarded_title["injections_detected"] or guarded_text["injections_detected"]:
            injection_notes.append("⚠️ Prompt injection attempts detected and sanitized.")

        claim_notes = []
        for claim, res in zip(claims, verification_results):
            statement_txt = getattr(claim, "statement", getattr(claim, "text", ""))
            status_val = res.status.value if hasattr(res.status, "value") else str(res.status)
            claim_notes.append(f"- {statement_txt[:80]}: {status_val} (conf={res.confidence:.2f})")

        narrative = f"## Analysis Summary for {story_id}\n\n"
        if injection_notes:
            narrative += " ".join(injection_notes) + "\n\n"
        narrative += f"**Topics**: {', '.join(topics)}\n\n"
        narrative += f"**Claims Extracted**: {len(claims)}\n"
        if claim_notes:
            narrative += "\n" + "\n".join(claim_notes) + "\n\n"
        narrative += f"**Overall Confidence**: {overall_confidence:.2f}"

        submission = AnalysisSubmission(
            analyst_id=analyst_id,
            story_id=story_id,
            submitted_at=datetime.now(timezone.utc),
            status=AnalysisStatus.DRAFT,
            claims=claims,
            evidence=evidence_pool,
            verification_results=verification_results,
            overall_confidence=overall_confidence,
            narrative_summary=narrative,
            topics=topics,
        )
        return submission

    async def submit_analysis(
        self,
        story_id: str,
        submission: AnalysisSubmission,
        api_base: str,
        agent_token: str,
    ) -> dict:
        url = f"{api_base.rstrip('/')}/agent/stories/{story_id}/analysis"
        payload = submission.model_dump(mode="json")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {agent_token}"},
            )
            response.raise_for_status()
            return response.json()


analyst_agent = AnalystAgent()
