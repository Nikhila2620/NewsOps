"""
NewsOps Revision 2 - Claim Contract (Pydantic v2).

Represents an atomic factual statement extracted from story text or documentation,
ready for provenance checking and independent verification.
"""

import uuid
from typing import Optional, Union
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    AliasChoices,
)

from .enums import ClaimType


class Claim(BaseModel):
    """
    Atomic claim extracted from story text.

    Complies with NewsOps Revision 2 Section 7.6 step 1:
    'Extract atomic claims (version, date, capability, benchmark, price, availability, license).'
    """
    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

    # Identifiers & Content
    claim_id: str = Field(
        default_factory=lambda: f"claim-{uuid.uuid4().hex[:8]}",
        validation_alias=AliasChoices("claim_id", "id"),
        description="Unique identifier for the atomic claim.",
    )
    statement: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        validation_alias=AliasChoices("statement", "claim", "text"),
        description="The atomic factual assertion extracted from the source material.",
    )
    claim_type: Union[ClaimType, str] = Field(
        default=ClaimType.GENERAL,
        description="Category of the claim (version, benchmark, capability, date, price, etc.).",
    )

    # Provenance & Extraction Metadata
    source_reference: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("source_reference", "source_ref", "source"),
        description="Location where claim appeared (e.g. 'README.md:lines 12-18', 'arXiv abstract').",
    )
    source_url: Optional[HttpUrl] = Field(
        default=None,
        description="Direct URL where the claim text was published.",
    )
    quote: Optional[str] = Field(
        default=None,
        max_length=1500,
        description="Verbatim untrusted quote from the source.",
    )
    is_vendor_claim: bool = Field(
        default=False,
        description="True if stated directly by tool author/vendor without third-party replication.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score in [0.0, 1.0].",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Associated software entities/packages (e.g. ['fastapi', 'pydantic']).",
    )

    @field_validator("statement")
    @classmethod
    def validate_statement(cls, v: str) -> str:
        trimmed = v.strip()
        if len(trimmed) < 3:
            raise ValueError("Claim statement must be at least 3 characters long.")
        return trimmed

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be in range [0.0, 1.0].")
        return round(float(v), 4)

    @field_validator("claim_type")
    @classmethod
    def normalize_claim_type(cls, v: Union[ClaimType, str]) -> Union[ClaimType, str]:
        if isinstance(v, str):
            try:
                return ClaimType(v.lower())
            except ValueError:
                return v
        return v
