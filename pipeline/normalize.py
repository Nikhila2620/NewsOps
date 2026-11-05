"""
NewsOps Revision 2 - Data Normalization Pipeline.
Canonicalizes URLs, parses dates, computes content_hash for deduplication.
"""
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs

def canonicalize_url(url: str) -> str:
    """
    Normalize a URL: strip tracking params, lowercase scheme/host, remove fragments.
    Removes utm_*, ref, source, fbclid query params.
    """
    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/") or "/"
        
        # Strip tracking and noise query params
        STRIP_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_content",
                        "utm_term", "ref", "source", "fbclid", "gclid", "mc_cid",
                        "mc_eid", "yclid", "_ga"}
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in STRIP_PARAMS}
        query = urlencode(sorted(clean_qs.items()), doseq=True)
        
        return urlunparse((scheme, netloc, path, "", query, ""))
    except Exception:
        return url

def compute_content_hash(title: str, text: str = "") -> str:
    """SHA-256 hash of normalized title+text for deduplication."""
    combined = f"{title.strip().lower()}|{text.strip().lower()}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()

def parse_date(date_str: Optional[str]) -> datetime:
    """Parse ISO 8601 or RFC 2822 date string to UTC datetime. Falls back to now()."""
    if not date_str:
        return datetime.now(timezone.utc)
    
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc)

def normalize_article(raw: dict) -> dict:
    """
    Normalize a raw article dict into a canonical form for deduplication and ranking.
    
    Input keys (from connectors): title, url, text, published_at, source_key, trust_tier, topics
    Output adds: canonical_url, content_hash, published_at (datetime), normalized_title
    """
    url = canonicalize_url(raw.get("url", ""))
    title = raw.get("title", "").strip()
    text = raw.get("text", raw.get("summary", raw.get("description", "")))
    published_at = parse_date(raw.get("published_at") or raw.get("created_at"))
    
    return {
        **raw,
        "url": url,
        "canonical_url": url,
        "title": title,
        "normalized_title": title.lower(),
        "text": str(text),
        "content_hash": compute_content_hash(title, str(text)),
        "published_at": published_at.isoformat(),
        "source_key": raw.get("source_key", "unknown"),
        "trust_tier": int(raw.get("trust_tier", 2)),
        "topics": raw.get("topics", []),
    }
