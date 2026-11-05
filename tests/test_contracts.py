"""
NewsOps Revision 2 - Pytest Test Suite for Contracts and Schemas.

Validates all 5 required models:
- Evidence
- Claim
- StoryAnalysis
- AnalysisSubmission
- VerificationResult

Tests exact evidence types and statuses, field validations, confidence bounds,
untrusted text handling, community signal rules, escalation rules, and JSON serialization.
"""

import json
import pytest
from pydantic import ValidationError

from newsops.contracts import (
    Evidence,
    Claim,
    StoryAnalysis,
    VerificationResult,
    AnalysisSubmission,
    EvidenceType,
    EvidenceStatus,
    ClaimType,
    TrustBadgeKind,
    AnalysisStatus,
)


# ==============================================================================
# 1. Enums Exact Values Tests
# ==============================================================================
def test_exact_evidence_types():
    expected_types = {
        "primary_source",
        "independent_reporting",
        "secondary_commentary",
        "community_signal",
        "user_provided",
    }
    actual_types = {t.value for t in EvidenceType}
    assert actual_types == expected_types, f"Evidence types mismatch. Got: {actual_types}"


def test_exact_evidence_statuses():
    expected_statuses = {
        "supported",
        "contradicted",
        "insufficient_evidence",
        "not_checked",
    }
    actual_statuses = {s.value for s in EvidenceStatus}
    assert actual_statuses == expected_statuses, f"Evidence statuses mismatch. Got: {actual_statuses}"


# ==============================================================================
# 2. Evidence Model Tests
# ==============================================================================
def test_evidence_valid_creation():
    ev = Evidence(
        evidence_url="https://github.com/fastapi/fastapi/releases/tag/0.115.0",
        evidence_type=EvidenceType.PRIMARY_SOURCE,
        source_reference="GitHub API release tag",
        status=EvidenceStatus.SUPPORTED,
        confidence=0.95,
        confidence_rationale="Verified with GitHub release tag.",
        claim="FastAPI 0.115 released.",
        claim_type=ClaimType.VERSION,
    )
    assert str(ev.evidence_url) == "https://github.com/fastapi/fastapi/releases/tag/0.115.0"
    assert ev.evidence_type == EvidenceType.PRIMARY_SOURCE
    assert ev.status == EvidenceStatus.SUPPORTED
    assert ev.confidence == 0.95

    # Test Member 1 MongoDB format mapping
    mongo_dict = ev.to_mongo_dict()
    assert mongo_dict["evidence_url"] == "https://github.com/fastapi/fastapi/releases/tag/0.115.0"
    assert mongo_dict["evidence_type"] == "primary_source"
    assert mongo_dict["status"] == "supported"
    assert mongo_dict["claim_type"] == "version"


def test_evidence_aliases():
    # Test 'url', 'type', 'source_ref', 'rationale' aliases
    ev = Evidence(
        url="https://example.com/source",
        type="independent_reporting",
        source_ref="TechCrunch article",
        status="supported",
        rationale="Corroborated by independent review.",
    )
    assert ev.evidence_type == EvidenceType.INDEPENDENT_REPORTING
    assert ev.source_reference == "TechCrunch article"
    assert ev.confidence_rationale == "Corroborated by independent review."


def test_evidence_invalid_url():
    with pytest.raises(ValidationError):
        Evidence(
            evidence_url="not-a-valid-url",
            evidence_type=EvidenceType.PRIMARY_SOURCE,
            source_reference="test",
        )


def test_evidence_confidence_bounds():
    # Confidence must be between 0.0 and 1.0
    with pytest.raises(ValidationError):
        Evidence(
            evidence_url="https://example.com",
            evidence_type=EvidenceType.PRIMARY_SOURCE,
            source_reference="test",
            confidence=1.5,
        )

    with pytest.raises(ValidationError):
        Evidence(
            evidence_url="https://example.com",
            evidence_type=EvidenceType.PRIMARY_SOURCE,
            source_reference="test",
            confidence=-0.1,
        )


def test_evidence_community_signal_cannot_support_claim():
    # NewsOps Revision 2 Rule: community_signal cannot be 'supported'
    with pytest.raises(ValidationError) as exc:
        Evidence(
            evidence_url="https://reddit.com/r/programming/post",
            evidence_type=EvidenceType.COMMUNITY_SIGNAL,
            source_reference="Reddit thread",
            status=EvidenceStatus.SUPPORTED,
        )
    assert "community_signal" in str(exc.value)


def test_evidence_contradicted_requires_rationale():
    # Contradicted evidence must state why it conflicts
    with pytest.raises(ValidationError) as exc:
        Evidence(
            evidence_url="https://example.com/page",
            evidence_type=EvidenceType.PRIMARY_SOURCE,
            source_reference="Official page",
            status=EvidenceStatus.CONTRADICTED,
            confidence_rationale="",
        )
    assert "confidence_rationale" in str(exc.value)


def test_evidence_insufficient_evidence_confidence_ceiling():
    # Insufficient evidence confidence is capped at 0.50
    ev = Evidence(
        evidence_url="https://example.com/unconfirmed",
        evidence_type=EvidenceType.SECONDARY_COMMENTARY,
        source_reference="Blog speculation",
        status=EvidenceStatus.INSUFFICIENT_EVIDENCE,
        confidence=0.90,
    )
    assert ev.confidence <= 0.50


# ==============================================================================
# 3. Claim Model Tests
# ==============================================================================
def test_claim_valid_creation():
    c = Claim(
        statement="Python 3.13 introduces free-threaded mode (PEP 703).",
        claim_type=ClaimType.CAPABILITY,
        source_reference="Python 3.13 What's New",
        source_url="https://docs.python.org/3.13/whatsnew/3.13.html",
        is_vendor_claim=True,
        confidence=0.99,
        entities=["python", "cpython"],
    )
    assert c.claim_id.startswith("claim-")
    assert c.statement == "Python 3.13 introduces free-threaded mode (PEP 703)."
    assert c.claim_type == ClaimType.CAPABILITY
    assert c.is_vendor_claim is True
    assert c.confidence == 0.99


def test_claim_statement_minimum_length():
    with pytest.raises(ValidationError):
        Claim(statement="no")


# ==============================================================================
# 4. StoryAnalysis Model Tests
# ==============================================================================
def test_story_analysis_valid_creation():
    sa = StoryAnalysis(
        summary="A major update to CPython 3.13 removes the Global Interpreter Lock experimentally.",
        why_it_matters="Allows multithreaded Python code to utilize all CPU cores without multiprocessing overhead.",
        practical_impact="Engineers can run concurrent CPU-bound workloads within a single process.",
        affected_users=["python-devs", "data-engineers", "backend-architects"],
        caveats=["C-extension packages must be compiled with free-threading support."],
        unknowns=["Performance degradation on single-threaded legacy code."],
    )
    assert sa.status == AnalysisStatus.COMPLETED
    assert sa.submitted_by == "newsops-analyst"
    assert len(sa.affected_users) == 3

    # Member 1 MongoDB format mapping
    mongo_dict = sa.to_mongo_dict()
    assert mongo_dict["summary"] == sa.summary
    assert mongo_dict["why_it_matters"] == sa.why_it_matters
    assert mongo_dict["practical_impact"] == sa.practical_impact
    assert mongo_dict["status"] == "completed"
    assert "submitted_at" in mongo_dict


def test_story_analysis_field_lengths():
    with pytest.raises(ValidationError):
        StoryAnalysis(
            summary="short",  # < 10 chars
            why_it_matters="Long enough explanation for matters.",
            practical_impact="Long enough daily developer explanation.",
            affected_users=["devs"],
        )


def test_story_analysis_empty_affected_users():
    with pytest.raises(ValidationError):
        StoryAnalysis(
            summary="Valid summary exceeding ten chars.",
            why_it_matters="Valid why it matters explanation.",
            practical_impact="Valid practical impact explanation.",
            affected_users=[],
        )


# ==============================================================================
# 5. VerificationResult Model Tests
# ==============================================================================
def test_verification_result_supported_primary():
    ev = Evidence(
        evidence_url="https://github.com/astral-sh/uv/releases/tag/0.5.0",
        evidence_type=EvidenceType.PRIMARY_SOURCE,
        source_reference="GitHub releases",
        status=EvidenceStatus.SUPPORTED,
        confidence=0.99,
    )
    vr = VerificationResult(
        claim_id="claim-uv-001",
        status=EvidenceStatus.SUPPORTED,
        confidence=0.99,
        rationale="Verified with GitHub release tag 0.5.0.",
        evidence=[ev],
    )
    assert vr.review_required is False
    assert vr.trust_badge == TrustBadgeKind.PRIMARY_API_VERIFIED
    assert str(vr.primary_evidence_url) == "https://github.com/astral-sh/uv/releases/tag/0.5.0"


def test_verification_result_auto_escalation_on_low_confidence():
    vr = VerificationResult(
        claim_id="claim-speculative-002",
        status=EvidenceStatus.NOT_CHECKED,
        confidence=0.55,  # < 0.70 threshold
        rationale="Preliminary check.",
    )
    assert vr.review_required is True


def test_verification_result_auto_escalation_on_contradiction():
    ev = Evidence(
        evidence_url="https://example.com/proof",
        evidence_type=EvidenceType.PRIMARY_SOURCE,
        source_reference="Official doc",
        status=EvidenceStatus.CONTRADICTED,
        confidence=0.95,
        confidence_rationale="Documentation contradicts claim.",
    )
    vr = VerificationResult(
        claim_id="claim-003",
        status=EvidenceStatus.CONTRADICTED,
        confidence=0.95,
        rationale="Direct contradiction discovered.",
        evidence=[ev],
    )
    assert vr.review_required is True
    assert vr.trust_badge == TrustBadgeKind.NEEDS_REVIEW


def test_verification_result_rejects_community_signal_alone_for_supported():
    ev = Evidence(
        evidence_url="https://news.ycombinator.com/item?id=12345",
        evidence_type=EvidenceType.COMMUNITY_SIGNAL,
        source_reference="Hacker News discussion",
        status=EvidenceStatus.NOT_CHECKED,
        confidence=0.60,
    )
    with pytest.raises(ValidationError) as exc:
        VerificationResult(
            claim_id="claim-004",
            status=EvidenceStatus.SUPPORTED,
            confidence=0.85,
            rationale="Supported by HN comments.",
            evidence=[ev],
        )
    assert "community_signal" in str(exc.value)


# ==============================================================================
# 6. AnalysisSubmission Model Tests
# ==============================================================================
def test_analysis_submission_valid_e2e():
    analysis = StoryAnalysis(
        summary="uv package manager released workspace support in version 0.5.",
        why_it_matters="Enables monorepo management with native Rust speed.",
        practical_impact="Engineers can run multi-package python builds in seconds.",
        affected_users=["python-devs"],
    )
    claim = Claim(
        claim_id="claim-uv-ws",
        statement="uv 0.5 adds full python workspace management.",
        claim_type=ClaimType.CAPABILITY,
    )
    ev = Evidence(
        evidence_url="https://github.com/astral-sh/uv/releases/tag/0.5.0",
        evidence_type=EvidenceType.PRIMARY_SOURCE,
        source_reference="GitHub Releases API",
        status=EvidenceStatus.SUPPORTED,
        confidence=0.98,
    )
    vr = VerificationResult(
        claim_id="claim-uv-ws",
        status=EvidenceStatus.SUPPORTED,
        confidence=0.98,
        rationale="Verified with GitHub API release tag.",
        evidence=[ev],
    )

    sub = AnalysisSubmission(
        story_id="story-uv-001",
        analysis=analysis,
        claims=[claim],
        verification_results=[vr],
    )

    assert sub.story_id == "story-uv-001"
    assert sub.review_required is False
    assert sub.overall_confidence == 0.98

    # Test MongoDB story update generation matching Member 1
    story_update = sub.to_story_update()
    assert "analysis" in story_update
    assert "evidence" in story_update
    assert "review_flag" in story_update
    assert "last_updated_at" in story_update
    assert story_update["review_flag"] is False
    assert len(story_update["evidence"]) == 1
    assert story_update["evidence"][0]["status"] == "supported"


def test_analysis_submission_rejects_unsourced_claims():
    # NewsOps Revision 2 Rule: Rejects malformed or unsourced output
    analysis = StoryAnalysis(
        summary="A new tool was announced without any evidence links or citations.",
        why_it_matters="Shows why verification is essential in developer tools.",
        practical_impact="Developers should be wary of unverified claims.",
        affected_users=["engineers"],
    )
    claim = Claim(
        statement="Tool claims 100x speedup with zero proof.",
        claim_type=ClaimType.BENCHMARK,
    )

    # Claims provided but NO evidence and NO verification results
    with pytest.raises(ValidationError) as exc:
        AnalysisSubmission(
            story_id="story-fake-001",
            analysis=analysis,
            claims=[claim],
            verification_results=[],
            evidence=[],
        )
    assert "unsourced output" in str(exc.value)


def test_analysis_submission_auto_escalates_review_on_contradiction():
    analysis = StoryAnalysis(
        summary="Conflicting statements regarding software licensing.",
        why_it_matters="License compliance is critical.",
        practical_impact="Do not integrate until confirmed.",
        affected_users=["legal", "devs"],
    )
    claim = Claim(statement="Claimed Apache 2.0 license.", claim_type=ClaimType.LICENSE)
    ev = Evidence(
        evidence_url="https://example.com/LICENSE",
        evidence_type=EvidenceType.PRIMARY_SOURCE,
        source_reference="Repository LICENSE file",
        status=EvidenceStatus.CONTRADICTED,
        confidence=0.99,
        confidence_rationale="LICENSE file specifies GPL.",
    )
    vr = VerificationResult(
        claim_id=claim.claim_id,
        status=EvidenceStatus.CONTRADICTED,
        confidence=0.99,
        rationale="Contradicted by LICENSE file.",
        evidence=[ev],
    )

    sub = AnalysisSubmission(
        story_id="story-lic-001",
        analysis=analysis,
        claims=[claim],
        verification_results=[vr],
    )

    assert sub.review_required is True
    story_update = sub.to_story_update()
    assert story_update["review_flag"] is True


def test_json_serialization_roundtrip():
    # Ensure full serialization and deserialization works cleanly
    analysis = StoryAnalysis(
        summary="Valid summary string exceeding ten characters.",
        why_it_matters="Valid why it matters explanation.",
        practical_impact="Valid practical impact explanation.",
        affected_users=["devs"],
    )
    ev = Evidence(
        evidence_url="https://github.com/repo",
        evidence_type=EvidenceType.PRIMARY_SOURCE,
        source_reference="GitHub",
        status=EvidenceStatus.SUPPORTED,
    )
    vr = VerificationResult(
        claim_id="claim-1",
        status=EvidenceStatus.SUPPORTED,
        confidence=0.95,
        rationale="Verified.",
        evidence=[ev],
    )
    sub = AnalysisSubmission(
        analysis=analysis,
        verification_results=[vr],
    )

    json_str = sub.model_dump_json()
    assert isinstance(json_str, str)

    # Roundtrip load
    data = json.loads(json_str)
    restored = AnalysisSubmission.model_validate(data)
    assert restored.analysis.summary == analysis.summary
    assert restored.verification_results[0].status == EvidenceStatus.SUPPORTED
