"""
NewsOps Revision 2 - AI Topic Classifier.
Wraps pipeline.classify with confidence scoring and ClaimType mapping.
"""
from typing import List, Tuple
from ..pipeline.classify import classify_topics
from ..contracts.enums import ClaimType


TOPIC_TO_CLAIM_TYPE = {
    "security": ClaimType.SECURITY,
    "aiml": ClaimType.CAPABILITY,
    "cloud": ClaimType.PERFORMANCE,
    "devtools": ClaimType.CAPABILITY,
    "data": ClaimType.PERFORMANCE,
    "web_backend": ClaimType.CAPABILITY,
    "oss": ClaimType.VERSION,
}


def classify_article(title: str, text: str = "", existing_topics: List[str] = None) -> dict:
    """
    Classify an article into topics and primary claim type.
    Returns {"topics": [...], "confidence": float, "primary_claim_type": ClaimType}.
    """
    topics, confidence = classify_topics(title, text, existing_topics or [])
    primary_topic = topics[0] if topics else "oss"
    primary_claim_type = TOPIC_TO_CLAIM_TYPE.get(primary_topic, ClaimType.CAPABILITY)

    return {
        "topics": topics,
        "confidence": confidence,
        "primary_claim_type": primary_claim_type,
        "primary_topic": primary_topic,
    }
