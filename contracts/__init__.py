"""
NewsOps Revision 2 - Shared JSON Contracts and Pydantic v2 Schemas.
Authored for Member 2 (AI/Verification) & Member 1 (Backend/Data).
"""

from .enums import (
    EvidenceType,
    EvidenceStatus,
    ClaimType,
    TrustBadgeKind,
    AnalysisStatus,
)
from .evidence import Evidence
from .claim import Claim
from .analysis import StoryAnalysis
from .verification import VerificationResult
from .submission import AnalysisSubmission

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
