"""
NewsOps Revision 2 - Source Model & MongoDB Document Schema.

Complies with NewsOps Revision 2 Section 6 (sources collection schema)
and Section 9 (GET /sources).
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SourceCreate(BaseModel):
    """Payload to register a new external news source."""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(..., min_length=2, description="Display name of source")
    type: str = Field(default="api", description="api, rss, or scraper")
    domain: str = Field(..., description="Canonical network domain")
    terms_url: str = Field(..., description="Terms of service / scraping policy URL")
    trust_tier: int = Field(default=2, ge=1, le=3, description="1=primary, 2=vendor/secondary, 3=community")
    enabled: bool = Field(default=True)


class Source(BaseModel):
    """
    MongoDB Source Document and API Model.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )

    id: str = Field(default="", alias="_id", description="Unique source ID")
    name: str = Field(..., min_length=2)
    type: str = Field(default="api")
    domain: str = Field(...)
    terms_url: str = Field(...)
    trust_tier: int = Field(default=2, ge=1, le=3)
    enabled: bool = Field(default=True)
    health: str = Field(default="ok", description="ok, degraded, or failing")
    last_ok_at: Optional[datetime] = Field(default=None)

    def to_mongo_dict(self) -> dict:
        d = self.model_dump(by_alias=True)
        if "_id" not in d or not d["_id"]:
            d["_id"] = self.id
        return d
