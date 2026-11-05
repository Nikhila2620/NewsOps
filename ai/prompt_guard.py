"""
NewsOps Revision 2 - Prompt Injection Guard.

Strips/neutralizes prompt injection attempts from untrusted README,
article text, or tool descriptions before they reach LLM or display.
"""
import re
from typing import Tuple

# Patterns that signal prompt injection attempts
INJECTION_PATTERNS = [
    # Direct instruction overrides
    (r"(?i)(ignore\s+(all\s+)?(previous|prior|above)\s+instructions?)", "override_instructions"),
    (r"(?i)(disregard\s+(all\s+)?(previous|prior|above)\s+instructions?)", "override_instructions"),
    (r"(?i)(forget\s+(everything|all)\s+(you\s+(know|were told)))", "forget_instructions"),
    # Role hijacking
    (r"(?i)(you\s+are\s+now\s+(a|an)\s+\w+)", "role_hijack"),
    (r"(?i)(act\s+as\s+(a|an)\s+(unrestricted|jailbroken|evil|dan)\b)", "jailbreak"),
    (r"(?i)\bDAN\b", "jailbreak"),
    # System prompt leakage
    (r"(?i)(print\s+(your\s+)?(system\s+prompt|instructions))", "system_prompt_leak"),
    (r"(?i)(reveal\s+(your\s+)?(system\s+prompt|instructions))", "system_prompt_leak"),
    # Exfiltration attempts
    (r"(?i)(send\s+(this|the)\s+(to|data)\s+http)", "exfiltration"),
    (r"(?i)(post\s+to\s+https?://)", "exfiltration"),
    # Delimiter injection
    (r"(?i)(---\s*system\s*---)", "delimiter_injection"),
    (r"(?i)(<\|im_start\|>|<\|im_end\|>)", "delimiter_injection"),
    # Command injection in context
    (r"(?i)(execute\s+(this|the\s+following)\s+(command|code|script))", "command_injection"),
]

REDACTION_PLACEHOLDER = "[REDACTED:INJECTION]"


def scan_for_injections(text: str) -> Tuple[bool, list]:
    """
    Scan text for prompt injection patterns.
    Returns (has_injection: bool, findings: list[dict]).
    """
    findings = []
    for pattern, name in INJECTION_PATTERNS:
        for match in re.finditer(pattern, text):
            findings.append({
                "pattern": name,
                "match": match.group(0)[:80],
                "start": match.start(),
            })
    return bool(findings), findings


def sanitize_text(text: str, max_length: int = 50000) -> str:
    """
    Sanitize untrusted text by:
    1. Redacting detected injection patterns
    2. Stripping null bytes and C0 control chars (except newline/tab)
    3. Truncating to max_length
    """
    if not text:
        return ""

    # Strip null bytes and dangerous control characters
    text = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", text)

    # Redact injection patterns
    for pattern, _ in INJECTION_PATTERNS:
        text = re.sub(pattern, REDACTION_PLACEHOLDER, text, flags=re.IGNORECASE)

    # Truncate
    if len(text) > max_length:
        text = text[:max_length] + "\n[TRUNCATED]"

    return text


def guard_input(text: str, source: str = "unknown") -> dict:
    """
    Full guard check: scan + sanitize.
    Returns {"clean": str, "injections_detected": bool, "findings": list, "source": str}.
    """
    has_injection, findings = scan_for_injections(text)
    clean = sanitize_text(text)
    return {
        "clean": clean,
        "injections_detected": has_injection,
        "findings": findings,
        "source": source,
    }
