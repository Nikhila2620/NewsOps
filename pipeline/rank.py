"""
NewsOps Revision 2 - Relevance Ranking Pipeline.
score = 0.35*relevance + 0.25*source_quality + 0.20*recency + 0.15*impact + 0.05*novelty
"""
import math
from datetime import datetime, timezone
from typing import List, Optional

# Trust tier → source quality score
TRUST_TIER_SCORE = {1: 1.0, 2: 0.65, 3: 0.40}

REASON_CODE_MAP = {
    "high_relevance": "relevance_score > 0.70",
    "primary_source": "trust_tier == 1",
    "secondary_source": "trust_tier == 2",
    "community_source": "trust_tier == 3",
    "recent": "published within 24h",
    "moderate_recency": "published within 72h",
    "high_impact": "impact_score > 0.70",
    "novel": "novelty_score > 0.70",
}


def compute_recency_score(published_at_iso: Optional[str]) -> float:
    """Exponential decay: 1.0 at 0h, ~0.5 at 24h, ~0.1 at 72h."""
    if not published_at_iso:
        return 0.3
    try:
        dt = datetime.fromisoformat(published_at_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return max(0.0, math.exp(-age_hours / 34.0))  # half-life 34h → 0.5 at 24h
    except (ValueError, TypeError):
        return 0.3


def compute_impact_score(article: dict) -> float:
    """
    Estimate impact from stars, comments, upvotes, or other engagement signals.
    Returns 0.0–1.0.
    """
    stars = article.get("stars", 0) or 0
    comments = article.get("num_comments", 0) or 0
    upvotes = article.get("score", 0) or 0
    
    # Log-scale normalization: 1000 stars/upvotes → ~1.0
    signal = stars + upvotes + (comments * 2)
    return min(1.0, math.log1p(signal) / math.log1p(1000))


def compute_rank_score(article: dict, relevance_score: float = 0.5, novelty_score: float = 0.5) -> dict:
    """
    Compute final rank_score and reason_codes for an article.
    Returns dict with rank_score and reason_codes added.
    """
    trust_tier = int(article.get("trust_tier", 2))
    source_quality = TRUST_TIER_SCORE.get(trust_tier, 0.65)
    recency = compute_recency_score(article.get("published_at"))
    impact = compute_impact_score(article)
    
    score = (
        0.35 * relevance_score
        + 0.25 * source_quality
        + 0.20 * recency
        + 0.15 * impact
        + 0.05 * novelty_score
    )
    score = round(min(1.0, max(0.0, score)), 4)
    
    reason_codes: List[str] = []
    if relevance_score > 0.70:
        reason_codes.append("high_relevance")
    if trust_tier == 1:
        reason_codes.append("primary_source")
    elif trust_tier == 2:
        reason_codes.append("secondary_source")
    else:
        reason_codes.append("community_source")
    
    published_at = article.get("published_at", "")
    try:
        dt = datetime.fromisoformat(published_at) if published_at else None
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt:
            age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            if age_h <= 24:
                reason_codes.append("recent")
            elif age_h <= 72:
                reason_codes.append("moderate_recency")
    except (ValueError, TypeError):
        pass
    
    if impact > 0.70:
        reason_codes.append("high_impact")
    if novelty_score > 0.70:
        reason_codes.append("novel")
    
    return {**article, "rank_score": score, "reason_codes": reason_codes}


def rank_articles(articles: List[dict], user_topics: List[str] = None) -> List[dict]:
    """Sort and score a list of normalized articles by rank_score descending."""
    if user_topics is None:
        user_topics = []
    
    ranked = []
    for article in articles:
        # Relevance: topic overlap
        article_topics = article.get("topics", [])
        if user_topics and article_topics:
            overlap = len(set(article_topics) & set(user_topics))
            relevance = min(1.0, 0.5 + (overlap / max(len(user_topics), 1)) * 0.5)
        else:
            relevance = 0.5
        
        ranked.append(compute_rank_score(article, relevance_score=relevance))
    
    return sorted(ranked, key=lambda a: a.get("rank_score", 0), reverse=True)
