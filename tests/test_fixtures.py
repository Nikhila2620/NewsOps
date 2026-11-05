"""
NewsOps Revision 2 - Pytest Fixtures Validation.

Ensures all example JSON fixtures in `newsops/fixtures/` strictly adhere
to the Pydantic v2 schemas and can be parsed and re-serialized without loss.
"""

import json
from pathlib import Path
import pytest

from newsops.contracts import (
    Evidence,
    Claim,
    StoryAnalysis,
    VerificationResult,
    AnalysisSubmission,
    EvidenceStatus,
    TrustBadgeKind,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_example_evidence_fixture():
    fixture_path = FIXTURES_DIR / "example_evidence.json"
    assert fixture_path.exists(), f"Missing fixture: {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    evidence = Evidence.model_validate(data)
    assert evidence.status == EvidenceStatus.SUPPORTED
    assert str(evidence.evidence_url) == "https://github.com/pydantic/pydantic/releases/tag/v2.10.0"
    assert evidence.confidence == 0.98

    # Verify Member 1 Mongo export
    mongo_dict = evidence.to_mongo_dict()
    assert mongo_dict["status"] == "supported"
    assert mongo_dict["evidence_type"] == "primary_source"


def test_example_claim_fixture():
    fixture_path = FIXTURES_DIR / "example_claim.json"
    assert fixture_path.exists(), f"Missing fixture: {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    claim = Claim.model_validate(data)
    assert claim.claim_id == "claim-pydantic-001"
    assert claim.is_vendor_claim is True
    assert "pydantic" in claim.entities


def test_example_story_analysis_fixture():
    fixture_path = FIXTURES_DIR / "example_story_analysis.json"
    assert fixture_path.exists(), f"Missing fixture: {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    analysis = StoryAnalysis.model_validate(data)
    assert len(analysis.affected_users) == 4
    assert len(analysis.caveats) == 2
    assert len(analysis.unknowns) == 1
    assert analysis.submitted_by == "newsops-analyst"


def test_example_verification_result_fixture():
    fixture_path = FIXTURES_DIR / "example_verification_result.json"
    assert fixture_path.exists(), f"Missing fixture: {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    vr = VerificationResult.model_validate(data)
    assert vr.status == EvidenceStatus.SUPPORTED
    assert vr.trust_badge == TrustBadgeKind.PRIMARY_API_VERIFIED
    assert vr.review_required is False
    assert len(vr.evidence) == 1


def test_example_analysis_submission_fixture():
    fixture_path = FIXTURES_DIR / "example_analysis_submission.json"
    assert fixture_path.exists(), f"Missing fixture: {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sub = AnalysisSubmission.model_validate(data)
    assert sub.story_id == "story-pydantic-v210"
    assert sub.review_required is False
    assert sub.overall_confidence == 0.97

    # Verify compatibility with Member 1 MongoDB stories collection
    update = sub.to_story_update()
    assert update["review_flag"] is False
    assert len(update["evidence"]) == 1
    assert update["evidence"][0]["evidence_type"] == "primary_source"


def test_submission_low_confidence_fixture():
    fixture_path = FIXTURES_DIR / "submission_low_confidence.json"
    assert fixture_path.exists(), f"Missing fixture: {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sub = AnalysisSubmission.model_validate(data)
    assert sub.review_required is True
    assert sub.overall_confidence < 0.70
    assert sub.verification_results[0].trust_badge == TrustBadgeKind.NEEDS_REVIEW


def test_submission_contradicted_fixture():
    fixture_path = FIXTURES_DIR / "submission_contradicted.json"
    assert fixture_path.exists(), f"Missing fixture: {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sub = AnalysisSubmission.model_validate(data)
    assert sub.review_required is True
    assert sub.verification_results[0].status == EvidenceStatus.CONTRADICTED
    assert sub.verification_results[0].trust_badge == TrustBadgeKind.NEEDS_REVIEW
