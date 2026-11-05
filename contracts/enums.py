"""
NewsOps Revision 2 - Shared Enums for Evidence & Verification Contracts.

Defines exact evidence types, evidence statuses, claim categories, and trust badges
as specified in the NewsOps Revision 2 Architecture Specification.
"""

from enum import Enum


class EvidenceType(str, Enum):
    """
    Exact evidence types specified by NewsOps Revision 2.

    Hierarchy & Provenance:
    - PRIMARY_SOURCE: Authoritative facts directly from official API, repository, release notes, or vendor spec.
    - INDEPENDENT_REPORTING: Third-party tech journalism or peer reproduction with corroboration.
    - SECONDARY_COMMENTARY: Blog posts, opinion pieces, or summaries citing external sources.
    - COMMUNITY_SIGNAL: Social discussion (Reddit, Hacker News). Used for discovery ONLY; never proves a claim.
    - USER_PROVIDED: Manual user submission or developer contribution.
    """
    PRIMARY_SOURCE = "primary_source"
    INDEPENDENT_REPORTING = "independent_reporting"
    SECONDARY_COMMENTARY = "secondary_commentary"
    COMMUNITY_SIGNAL = "community_signal"
    USER_PROVIDED = "user_provided"


class EvidenceStatus(str, Enum):
    """
    Exact evidence evaluation statuses specified by NewsOps Revision 2.

    - SUPPORTED: Factual claim is substantiated by valid evidence.
    - CONTRADICTED: Evidence directly refutes or conflicts with the claim.
    - INSUFFICIENT_EVIDENCE: Available data is inadequate to verify the claim; routes to human review.
    - NOT_CHECKED: Initial default state before verification has executed.
    """
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_CHECKED = "not_checked"


class ClaimType(str, Enum):
    """
    Atomic claim categories specified by NewsOps Revision 2 (Section 7.6).
    """
    VERSION = "version"
    DATE = "date"
    CAPABILITY = "capability"
    BENCHMARK = "benchmark"
    PRICE = "price"
    AVAILABILITY = "availability"
    LICENSE = "license"
    PERFORMANCE = "performance"
    SECURITY = "security"
    GENERAL = "general"


class TrustBadgeKind(str, Enum):
    """
    Public trust badges defined by NewsOps Revision 2 (Section 7.6 and Part 3 Section 4).
    Never display the word 'Verified' alone.
    """
    PRIMARY_API_VERIFIED = "Primary (API-verified)"
    VENDOR_REPORTED = "Vendor-reported"
    COMMUNITY_SIGNAL = "Community signal"
    NEEDS_REVIEW = "Needs review"


class AnalysisStatus(str, Enum):
    """
    Lifecycle status of a StoryAnalysis.
    """
    COMPLETED = "completed"
    REVIEW_REQUIRED = "review_required"
    NEEDS_REVISION = "needs_revision"
    DRAFT = "draft"
