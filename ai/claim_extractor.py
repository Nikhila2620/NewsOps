"""
NewsOps Revision 2 - Claim Extractor.

Extracts atomic verifiable claims from story text using pattern matching.
Outputs Claim models matching contracts/claim.py.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import List

from ..contracts.claim import Claim
from ..contracts.enums import ClaimType, EvidenceStatus

CLAIM_PATTERNS = [
    # Version/release claims
    (r"\b(v\d+\.\d+[\.\d]*(?:\s*[-–]\s*[\w\s]+)?)\b.*(?:release|launch|ship|announc)", ClaimType.VERSION),
    (r"(?:releases?|launches?|ships?|announces?)\s+(?:v[\d\.]+|version\s+[\d\.]+)", ClaimType.VERSION),
    # Performance claims with numbers
    (r"\d+[x×]\s+(?:faster|slower|more efficient|better|worse)", ClaimType.PERFORMANCE),
    (r"(?:improve[sd]?|reduc[esd]+|increas[esd]+)\s+(?:performance|speed|latency|throughput)\s+by\s+\d+", ClaimType.PERFORMANCE),
    (r"(?:benchmark|performance).*(?:\d+%|\d+x)", ClaimType.BENCHMARK),
    # Vulnerability / CVE
    (r"CVE-\d{4}-\d{4,7}", ClaimType.SECURITY),
    (r"(?:vulnerabilit|exploit|remote code execution|RCE|XSS|SSRF|CSRF|SQL injection)", ClaimType.SECURITY),
    # Capability claims
    (r"(?:support[s]?|enable[s]?|allow[s]?|can now|introduces?)\s+(?:\w+\s+){1,4}(?:feature|capabilit|functionalit)", ClaimType.CAPABILITY),
    # Comparison claims
    (r"(?:better|worse|faster|slower|more|less)\s+than\s+\w+", ClaimType.BENCHMARK),
]


def extract_claims(title: str, text: str, story_id: str = "") -> List[Claim]:
    """
    Extract atomic claims from story title and text.
    Returns list of Claim objects with status=not_checked.
    """
    combined = f"{title}. {text}"
    sentences = re.split(r"(?<=[.!?])\s+", combined)

    claims: List[Claim] = []
    seen_texts = set()

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue

        for pattern, claim_type in CLAIM_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                normalized = sentence.lower()[:100]
                if normalized in seen_texts:
                    break
                seen_texts.add(normalized)

                claim = Claim(
                    id=f"claim-{uuid.uuid4().hex[:8]}",
                    story_id=story_id or "",
                    text=sentence[:500],
                    claim_type=claim_type,
                    status=EvidenceStatus.NOT_CHECKED,
                    confidence=0.0,
                    extracted_at=datetime.now(timezone.utc),
                )
                claims.append(claim)
                break  # one claim type per sentence

    return claims[:10]  # cap at 10 claims per story
