# NewsOps Revision 2 — Shared JSON Contracts & Pydantic v2 Schemas

> **Specification Reference**: NewsOps Revision 2 (Hackathon 4–7 Nov 2026), Part 1 §4, Part 2 §6, §7.6, §7.8, §9, Part 3 §6.  
> **Authors**: Member 2 (AI / Verification) in lockstep alignment with Member 1 (Backend / Data).

---

## 1. Architectural Role & Responsibilities

In NewsOps Revision 2:
- **Member 1 (Backend/Data)**: Owns ingestion, MongoDB 7 schema and indexes, FastAPI endpoints (`/healthz`, `/api/v1/stories`, `/api/v1/agent/*`), and task management.
- **Member 2 (AI/Verification)**: Owns the claim extraction, shared JSON contracts, Pydantic v2 verification models, trust badge derivation, and validation for `POST /api/v1/agent/stories/{id}/analysis`.

These models guarantee that no agent can inject hallucinated claims, malformed schemas, or unsourced assertions into Member 1's MongoDB database.

---

## 2. Core Models Specification

### 2.1 `Evidence`
Represents an external artifact proving or refuting a claim.

| Field | Type | Validation / Constraints | Description |
|---|---|---|---|
| `evidence_url` | `HttpUrl` (alias: `url`) | Valid HTTP/HTTPS URL | Link to external proof artifact |
| `evidence_type` | `EvidenceType` (alias: `type`) | One of the 5 exact specification values | Provenance classification tier |
| `source_reference` | `str` (alias: `source_ref`) | Min length 1, whitespace stripped | Source description (e.g. `GitHub API release tag v2.10`) |
| `status` | `EvidenceStatus` | Default: `not_checked` | Verification status |
| `confidence` | `float` | `0.0 <= confidence <= 1.0` | Confidence in finding |
| `confidence_rationale` | `Optional[str]` (alias: `rationale`) | Required if status is `contradicted` | Justification for confidence and status |
| `claim` | `Optional[str]` | Optional string statement | The claim statement being evaluated |
| `claim_type` | `Optional[Union[ClaimType, str]]` | Enum or string | Category of the claim |
| `claim_id` | `Optional[str]` | Optional string ID | ID of associated Claim model |
| `excerpt` | `Optional[str]` | Max 2000 chars | Untrusted source excerpt (data only) |
| `retrieved_at` | `Optional[datetime]` | UTC ISO-8601 | Fetch timestamp |
| `metadata` | `dict[str, Any]` | Default empty dict | Extra provenance metadata (SHA, stars, CVE) |

#### Exact Specification Values
**`EvidenceType`**:
- `primary_source`: Facts read straight from GitHub API, vendor release notes, or security advisories.
- `independent_reporting`: Corroborated tech journalism or third-party reproduction.
- `secondary_commentary`: Blog posts, community articles, opinion summaries.
- `community_signal`: Reddit or Hacker News posts. **Discovery only; never proves a claim.**
- `user_provided`: Explicit user submission or human annotation.

**`EvidenceStatus`**:
- `supported`: Verified and confirmed by evidence.
- `contradicted`: Disproven or in direct conflict with evidence.
- `insufficient_evidence`: Insufficient data available to verify; routes to human review.
- `not_checked`: Initial pending state.

---

### 2.2 `Claim`
Represents an atomic factual statement extracted from story text or repository documentation.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `claim_id` | `str` (alias: `id`) | Unique string (e.g. `claim-001`) | Identifier for the atomic claim |
| `statement` | `str` (alias: `claim`, `text`) | Min length 3 | The factual assertion |
| `claim_type` | `ClaimType` | Default: `general` | Category (`version`, `benchmark`, `capability`, `license`, etc.) |
| `source_reference` | `Optional[str]` | String | Location in text (e.g. `README.md:L12`) |
| `source_url` | `Optional[HttpUrl]` | Valid URL | Source URL |
| `is_vendor_claim` | `bool` | Default: `False` | True if self-reported by vendor without third-party proof |
| `confidence` | `float` | `0.0 <= confidence <= 1.0` | Extraction confidence |
| `quote` | `Optional[str]` | Max 1500 chars | Verbatim source quote |
| `entities` | `list[str]` | Package/repo names | Extracted entities for dependency impact matching |

---

### 2.3 `VerificationResult`
Represents the evaluation of a `Claim` against `Evidence` items.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `claim_id` | `str` | Min length 1 | ID of evaluated claim |
| `status` | `EvidenceStatus` | Required | Determination status |
| `confidence` | `float` | `0.0 <= confidence <= 1.0` | Verification confidence |
| `rationale` | `str` | Min length 3 | Transparent justification |
| `claim` | `Optional[Claim]` | Optional embedded Claim | Embedded claim object |
| `evidence` | `list[Evidence]` | List of evidence items | Evidence items checked |
| `primary_evidence_url` | `Optional[HttpUrl]` | Valid URL | Primary evidence URL if verified |
| `trust_badge` | `Optional[TrustBadgeKind]` | Auto-computed or explicit | Badge: `Primary (API-verified)`, `Vendor-reported`, `Community signal`, `Needs review` |
| `review_required` | `bool` | Auto-escalated | Forces `True` if `contradicted`, `insufficient_evidence`, or `confidence < 0.70` |

---

### 2.4 `StoryAnalysis`
Represents the narrative, contextual, and practical evaluation generated by the Analyst agent.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `summary` | `str` | Min length 10 | Concise, factual summary |
| `why_it_matters` | `str` | Min length 10 | Strategic significance |
| `practical_impact` | `str` (alias: `daily_life_use`) | Min length 10 | Daily-life use: how this helps in day-to-day engineering work |
| `affected_users` | `list[str]` | Min 1 non-empty persona | Impacted developer personas / tech stacks |
| `caveats` | `list[str]` | Default empty list | Limitations and constraints |
| `unknowns` | `list[str]` | Default empty list | Missing benchmark proofs or open questions |
| `submitted_by` | `str` | Default: `newsops-analyst` | Analyst agent identifier |
| `submitted_at` | `datetime` | UTC ISO-8601 | Generation timestamp |
| `status` | `Union[AnalysisStatus, str]` | Default: `completed` | Lifecycle state (`completed`, `review_required`, `draft`) |
| `confidence` | `Optional[float]` | `0.0 <= confidence <= 1.0` | Subjective analysis confidence |

---

### 2.5 `AnalysisSubmission`
The authoritative payload model accepted by:  
`POST /api/v1/agent/stories/{id}/analysis`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `story_id` | `Optional[str]` | Must match path `{id}` if provided | Target story ID |
| `analysis` | `StoryAnalysis` | Required | Narrative analysis |
| `claims` | `list[Claim]` | Default empty list | Extracted atomic claims |
| `verification_results` | `list[VerificationResult]` | Default empty list | Claim verification evaluations |
| `evidence` | `list[Evidence]` | Default empty list | Top-level evidence items |
| `overall_confidence` | `float` | `0.0 <= confidence <= 1.0` | Composite confidence score |
| `review_required` | `bool` (alias: `review_flag`) | Auto-escalated | True if any result requires review or confidence < 0.70 |
| `agent_id` | `str` (alias: `submitted_by`) | Default: `newsops-analyst` | Agent handle submitting analysis |
| `submitted_at` | `datetime` | UTC ISO-8601 | Submission timestamp |

---

## 3. Member 1 MongoDB Document Alignment

Member 1's MongoDB `stories` collection document (Revision 2 Section 6) requires:
```json
{
  "_id": "story-uuid-or-slug",
  "title": "Story Title",
  "topics": ["aiml", "cloud"],
  "evidence": [
    {
      "claim": "Claim statement",
      "claim_type": "version",
      "evidence_url": "https://...",
      "evidence_type": "primary_source",
      "status": "supported",
      "confidence_rationale": "Verified through official GitHub release tag."
    }
  ],
  "analysis": {
    "summary": "...",
    "why_it_matters": "...",
    "practical_impact": "...",
    "affected_users": ["python-devs"],
    "caveats": ["..."],
    "unknowns": ["..."],
    "submitted_by": "newsops-analyst",
    "submitted_at": "2026-11-04T12:00:00Z",
    "status": "completed"
  },
  "review_flag": false,
  "last_updated_at": "2026-11-04T12:00:00Z"
}
```

The method `submission.to_story_update()` generates this exact document structure automatically, ensuring zero discrepancy between Member 2's validation layer and Member 1's persistence layer.

---

## 4. Key Validation Rules Enforced

1. **Rejection of Unsourced Output**:
   If `claims` are provided, there must be at least one piece of `evidence` or `verification_result`. Submissions with unverified claims and no sources raise a `422 Unprocessable Entity`.
2. **Community Signal Restriction**:
   `community_signal` (Reddit, Hacker News) cannot independently yield `status: "supported"`. It can raise discovery ranking, but factual proof requires primary or independent evidence.
3. **Automatic Human Review Escalation**:
   `review_required` is automatically set to `True` if:
   - Any claim has status `contradicted` or `insufficient_evidence`.
   - Overall confidence falls below `0.70`.
4. **Contradiction Rationale Mandate**:
   Any `contradicted` evidence item must include a non-empty `confidence_rationale` explaining why the claim conflicts with the source.
5. **Trust Badge Auto-Derivation**:
   Badges are calculated transparently:
   - `Primary (API-verified)`: Factual claim backed by `primary_source` with status `supported`.
   - `Vendor-reported`: Claim self-reported by vendor without independent verification.
   - `Community signal`: Discussion discovery only.
   - `Needs review`: Any contradicted or insufficient evidence item.
