"""
NewsOps Revision 2 - Deduplication Pipeline.
Exact URL/hash deduplication + rapidfuzz token_set_ratio >= 88 within 72h window.
"""
import re
from datetime import datetime, timezone, timedelta
from typing import List, Tuple

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

FUZZY_THRESHOLD = 88  # token_set_ratio threshold for near-duplicate detection
WINDOW_HOURS = 72     # Only compare articles within 72-hour window


def is_duplicate(
    candidate: dict,
    existing: List[dict],
) -> Tuple[bool, str]:
    """
    Check if `candidate` is a duplicate of any article in `existing`.
    
    Returns (is_dup, reason_string).
    Checks in order:
    1. Exact canonical_url match
    2. Exact content_hash match
    3. Fuzzy title match (rapidfuzz token_set_ratio >= 88) within 72h window
    """
    candidate_url = candidate.get("canonical_url", candidate.get("url", ""))
    candidate_hash = candidate.get("content_hash", "")
    candidate_title = candidate.get("normalized_title", candidate.get("title", "")).lower()
    
    try:
        candidate_dt = datetime.fromisoformat(candidate.get("published_at", ""))
        if candidate_dt.tzinfo is None:
            candidate_dt = candidate_dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        candidate_dt = datetime.now(timezone.utc)
    
    window_start = candidate_dt - timedelta(hours=WINDOW_HOURS)
    
    for article in existing:
        # 1. Exact URL
        existing_url = article.get("canonical_url", article.get("url", ""))
        if candidate_url and existing_url and candidate_url == existing_url:
            return True, f"exact_url:{existing_url}"
        
        # 2. Exact hash
        existing_hash = article.get("content_hash", "")
        if candidate_hash and existing_hash and candidate_hash == existing_hash:
            return True, f"exact_hash:{existing_hash[:16]}"
        
        # 3. Fuzzy title within time window
        if HAS_RAPIDFUZZ and candidate_title:
            existing_title = article.get("normalized_title", article.get("title", "")).lower()
            try:
                article_dt = datetime.fromisoformat(article.get("published_at", ""))
                if article_dt.tzinfo is None:
                    article_dt = article_dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                article_dt = datetime.now(timezone.utc)
            
            if article_dt >= window_start:
                score = fuzz.token_set_ratio(candidate_title, existing_title)
                if score >= FUZZY_THRESHOLD:
                    return True, f"fuzzy_title:{score:.0f}"
    
    return False, ""


def deduplicate_batch(articles: List[dict]) -> List[dict]:
    """
    Remove duplicates from a list of articles. 
    Returns unique articles preserving insertion order (first occurrence kept).
    """
    unique: List[dict] = []
    for article in articles:
        is_dup, _ = is_duplicate(article, unique)
        if not is_dup:
            unique.append(article)
    return unique
