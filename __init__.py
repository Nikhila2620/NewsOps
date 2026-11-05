"""
NewsOps Core Package - Shared Contracts and Pydantic v2 Schemas.
"""

from .contracts import (
    EvidenceType,
    EvidenceStatus,
    ClaimType,
    TrustBadgeKind,
    AnalysisStatus,
    Evidence,
    Claim,
    StoryAnalysis,
    VerificationResult,
    AnalysisSubmission,
)

__all__ = [
    "EvidenceType",
    "EvidenceStatus",
    "ClaimType",
    "TrustBadgeKind",
    "AnalysisStatus",
    "Evidence",
    "Claim",
    "StoryAnalysis",
    "VerificationResult",
    "AnalysisSubmission",
]
