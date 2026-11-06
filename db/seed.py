"""
NewsOps Revision 2 - Initial Seed Data.

Populates initial database state idempotently on startup:
- Default rooms (#aiml, #cloud, #security) with interest rules and approvers
- Demo developer personas and profiles
- Ingestion sources with trust tiers
- Offline rich stories (>=12 across 3 rooms) with evidence, claims, install commands, advisories
- Community radar items
"""

from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..config.settings import settings
from ..core.logging import logger


INITIAL_ROOMS = [
    {
        "_id": "room-aiml-001",
        "key": "aiml",
        "name": "AI/ML Intelligence",
        "topics": ["aiml", "llm", "agents"],
        "rules": {
            "min_score": 0.60,
            "min_confidence": 0.70,
            "max_items": 8,
            "priorities": ["llm", "agents", "rag", "eval"],
            "blocked": [],
        },
        "approvers": ["lead_reviewer", "alice_aiml", "@nikhila", "nikhila"],
        "members": [{"user_id": "user-001", "role": "admin"}],
        "chat_platform": "mattermost",
        "chat_channel_id": "channel-aiml",
        "switch_room_ref": "switch:room:aiml",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "room-cloud-002",
        "key": "cloud",
        "name": "Cloud & Platform Eng",
        "topics": ["cloud", "devtools", "infrastructure"],
        "rules": {
            "min_score": 0.55,
            "min_confidence": 0.70,
            "max_items": 8,
            "priorities": ["kubernetes", "terraform", "observability"],
            "blocked": [],
        },
        "approvers": ["lead_reviewer", "sam_cloud", "bob_cloud", "@nikhila", "nikhila"],
        "members": [{"user_id": "user-002", "role": "admin"}],
        "chat_platform": "mattermost",
        "chat_channel_id": "channel-cloud",
        "switch_room_ref": "switch:room:cloud",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "room-sec-003",
        "key": "security",
        "name": "Security & Supply Chain",
        "topics": ["security", "advisories", "cve"],
        "rules": {
            "min_score": 0.70,
            "min_confidence": 0.70,
            "max_items": 8,
            "priorities": ["cve", "advisories", "secrets", "supply_chain"],
            "blocked": [],
        },
        "approvers": ["lead_reviewer", "alice_aiml", "@nikhila", "nikhila"],
        "members": [{"user_id": "user-003", "role": "admin"}],
        "chat_platform": "mattermost",
        "chat_channel_id": "channel-security",
        "switch_room_ref": "switch:room:security",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
]

INITIAL_USERS = [
    {
        "_id": "user-001",
        "display_name": "Alice Chen",
        "chat_handle": "alice_aiml",
        "github_login": "alice-dev",
        "topics": ["aiml", "oss"],
        "blocked_topics": [],
        "experience": "senior",
        "priorities": ["agents", "rag"],
        "approver_rooms": ["aiml", "security"],
        "digest_frequency": "daily",
        "quiet_hours": "22:00-08:00",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "user-sam-001",
        "display_name": "Sam Rivera",
        "chat_handle": "sam_cloud",
        "github_login": "sam-dev",
        "topics": ["cloud", "infrastructure"],
        "blocked_topics": [],
        "experience": "senior",
        "priorities": ["kubernetes", "terraform"],
        "approver_rooms": ["cloud"],
        "digest_frequency": "daily",
        "quiet_hours": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "user-002",
        "display_name": "Bob Martinez",
        "chat_handle": "bob_cloud",
        "github_login": "bob-ops",
        "topics": ["cloud", "devtools"],
        "blocked_topics": [],
        "experience": "lead",
        "priorities": ["kubernetes", "security"],
        "digest_frequency": "daily",
        "quiet_hours": "23:00-07:00",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "user-003",
        "display_name": "Chief Editor",
        "chat_handle": "lead_reviewer",
        "github_login": "lead-reviewer",
        "topics": ["aiml", "cloud", "security"],
        "blocked_topics": [],
        "experience": "principal",
        "priorities": ["quality", "provenance"],
        "digest_frequency": "realtime",
        "quiet_hours": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
]

INITIAL_SOURCES = [
    {
        "_id": "source-gh-001",
        "name": "GitHub Trending & Releases",
        "type": "api",
        "domain": "api.github.com",
        "terms_url": "https://docs.github.com/en/site-policy/github-terms/github-terms-of-service",
        "trust_tier": 1,
        "enabled": True,
        "health": "ok",
        "last_ok_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "source-hn-002",
        "name": "Hacker News (Algolia API)",
        "type": "api",
        "domain": "hn.algolia.com",
        "terms_url": "https://www.ycombinator.com/legal/",
        "trust_tier": 3,
        "enabled": True,
        "health": "ok",
        "last_ok_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "source-osv-003",
        "name": "OSV Vulnerability Database",
        "type": "api",
        "domain": "api.osv.dev",
        "terms_url": "https://osv.dev/about",
        "trust_tier": 1,
        "enabled": True,
        "health": "ok",
        "last_ok_at": datetime.now(timezone.utc).isoformat(),
    },
]

# 12 Realistic stories (4 per room) for offline & demo resilience
INITIAL_STORIES = [
    # --- AIML (4) ---
    {
        "_id": "story-aiml-001",
        "title": "vLLM v0.6.4: Speculative Decoding & Chunked Prefill Acceleration",
        "summary": "vLLM release introduces hardware-optimized speculative decoding reducing TTFT by 32% for Llama 3 models.",
        "room_key": "aiml",
        "topics": ["aiml", "llm"],
        "source_domain": "github.com",
        "source_url": "https://github.com/vllm-project/vllm/releases/tag/v0.6.4",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "rank_score": 0.94,
        "confidence": 0.96,
        "impact": "High speedup for enterprise local LLM inference engines",
        "trust_badge": "primary",
        "badge": "primary",
        "install_command": "pip install vllm>=0.6.4",
        "install_commit": "a1b2c3d4e5f67890abcdef1234567890abcdef12",
        "commit_sha": "a1b2c3d4e5f67890abcdef1234567890abcdef12",
        "risk_flags": [],
        "seeded": True,
        "review_flag": False,
        "members": [
            {"article_id": "art-01", "url": "https://github.com/vllm-project/vllm", "title": "vLLM Release v0.6.4", "publisher": "GitHub", "trust_tier": 1}
        ],
        "evidence": [
            {"evidence_url": "https://github.com/vllm-project/vllm/releases/tag/v0.6.4", "evidence_type": "primary_source", "source_reference": "GitHub Release Notes", "status": "supported", "confidence": 0.98}
        ],
        "claims": [
            {"claim_id": "c-01", "claim_text": "vLLM v0.6.4 supports multi-step speculative decoding", "claim_type": "CAPABILITY", "status": "supported"}
        ],
    },
    {
        "_id": "story-aiml-002",
        "title": "Ollama Distributed: Multi-Node Model Sharding Support",
        "summary": "Ollama adds experimental clustering across multiple LAN nodes using gRPC model weight streaming.",
        "room_key": "aiml",
        "topics": ["aiml", "agents"],
        "source_domain": "ollama.com",
        "source_url": "https://github.com/ollama/ollama/releases/tag/v0.4.1",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "rank_score": 0.88,
        "confidence": 0.89,
        "impact": "Local clustering for massive 70B+ weights without enterprise GPUs",
        "trust_badge": "vendor_reported",
        "badge": "vendor_reported",
        "install_command": "curl -fsSL https://ollama.com/install.sh | sh",
        "install_commit": "f4e3d2c1b0a98765fedcba0987654321fedcba09",
        "commit_sha": "f4e3d2c1b0a98765fedcba0987654321fedcba09",
        "risk_flags": ["network_pipe_to_shell"],
        "seeded": True,
        "review_flag": False,
        "members": [
            {"article_id": "art-02", "url": "https://ollama.com/blog/multi-node", "title": "Ollama Multi-Node Overview", "publisher": "Ollama Blog", "trust_tier": 2}
        ],
        "evidence": [
            {"evidence_url": "https://github.com/ollama/ollama/releases/tag/v0.4.1", "evidence_type": "primary_source", "source_reference": "GitHub API release", "status": "supported", "confidence": 0.92}
        ],
        "claims": [
            {"claim_id": "c-02", "claim_text": "Ollama installs via shell script on POSIX systems", "claim_type": "CAPABILITY", "status": "supported"}
        ],
    },
    {
        "_id": "story-aiml-003",
        "title": "FastEmbed 0.4.0 ONNX Micro-Embedding Claims (<0.70 Confidence)",
        "summary": "Uncorroborated Reddit benchmark claims FastEmbed achieves 10x throughput over SentenceTransformers without GPU.",
        "room_key": "aiml",
        "topics": ["aiml"],
        "source_domain": "reddit.com",
        "source_url": "https://www.reddit.com/r/MachineLearning/comments/xyz123/fastembed_benchmark",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "rank_score": 0.65,
        "confidence": 0.58,  # Under 0.70 -> triggers review_required
        "impact": "Unverified speedup benchmark for vector pipelines",
        "trust_badge": "community_signal",
        "badge": "community_signal",
        "install_command": "pip install fastembed",
        "install_commit": "1234567890abcdef1234567890abcdef12345678",
        "commit_sha": "1234567890abcdef1234567890abcdef12345678",
        "risk_flags": [],
        "seeded": True,
        "review_flag": True,
        "members": [
            {"article_id": "art-03", "url": "https://reddit.com/r/MachineLearning/comments/xyz123", "title": "FastEmbed 10x Claim", "publisher": "Reddit r/MachineLearning", "trust_tier": 3}
        ],
        "evidence": [
            {"evidence_url": "https://reddit.com/r/MachineLearning/comments/xyz123", "evidence_type": "community_signal", "source_reference": "Reddit community post", "status": "insufficient_evidence", "confidence": 0.45}
        ],
        "claims": [
            {"claim_id": "c-03", "claim_text": "FastEmbed achieves 10x throughput without GPU", "claim_type": "BENCHMARK", "status": "insufficient_evidence"}
        ],
    },
    {
        "_id": "story-aiml-004",
        "title": "Whisper.cpp Metal Kernel Speedup Claim (Contradicted by Official Benchmarks)",
        "summary": "Community blog claims 8x Metal performance boost, directly contradicted by Apple Silicon MLX team reproducibility tests.",
        "room_key": "aiml",
        "topics": ["aiml"],
        "source_domain": "hacker-news.firebaseio.com",
        "source_url": "https://news.ycombinator.com/item?id=3891000",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "rank_score": 0.62,
        "confidence": 0.85,
        "impact": "Conflicting performance claims on Apple Silicon inference",
        "trust_badge": "community_signal",
        "badge": "community_signal",
        "risk_flags": [],
        "seeded": True,
        "review_flag": True,
        "members": [
            {"article_id": "art-04", "url": "https://news.ycombinator.com/item?id=3891000", "title": "HN Whisper discussion", "publisher": "Hacker News", "trust_tier": 3}
        ],
        "evidence": [
            {"evidence_url": "https://github.com/ml-explore/mlx/issues/999", "evidence_type": "primary_source", "source_reference": "Official MLX Benchmark Matrix", "status": "contradicted", "confidence": 0.95, "confidence_rationale": "Direct contradiction: MLX benchmark suite demonstrated only 1.1x speedup."}
        ],
        "claims": [
            {"claim_id": "c-04", "claim_text": "Metal kernel provides 8x real-world audio transcription throughput", "claim_type": "BENCHMARK", "status": "contradicted"}
        ],
    },

    # --- CLOUD (4) ---
    {
        "_id": "story-cloud-001",
        "title": "Kubernetes 1.32 'Gateway API v1.2' Controller Integration",
        "summary": "Official Kubernetes release graduates Gateway API HTTPRoute and GRPCRoute to GA with multi-cluster egress.",
        "room_key": "cloud",
        "topics": ["cloud", "infrastructure"],
        "source_domain": "github.com",
        "source_url": "https://github.com/kubernetes/kubernetes/releases/tag/v1.32.0",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "rank_score": 0.93,
        "confidence": 0.97,
        "impact": "Standardization of cloud native ingress and traffic routing",
        "trust_badge": "primary",
        "badge": "primary",
        "install_command": "kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml",
        "install_commit": "b2c3d4e5f6a17890abcdef1234567890abcdef12",
        "commit_sha": "b2c3d4e5f6a17890abcdef1234567890abcdef12",
        "risk_flags": [],
        "seeded": True,
        "review_flag": False,
        "members": [
            {"article_id": "art-05", "url": "https://kubernetes.io/blog/2026/gateway-api-ga", "title": "Gateway API GA", "publisher": "Kubernetes Blog", "trust_tier": 1}
        ],
        "evidence": [
            {"evidence_url": "https://github.com/kubernetes/kubernetes/releases/tag/v1.32.0", "evidence_type": "primary_source", "source_reference": "Kubernetes GitHub release notes", "status": "supported", "confidence": 0.99}
        ],
        "claims": [
            {"claim_id": "c-05", "claim_text": "Gateway API v1.2 is generally available in Kubernetes 1.32", "claim_type": "VERSION", "status": "supported"}
        ],
    },
    {
        "_id": "story-cloud-002",
        "title": "OpenTofu 1.9.0: Encrypted State Files at Rest with AWS KMS / GCP KMS",
        "summary": "OpenTofu adds declarative client-side state encryption with automated key rotation and HSM backing.",
        "room_key": "cloud",
        "topics": ["cloud", "devtools"],
        "source_domain": "opentofu.org",
        "source_url": "https://github.com/opentofu/opentofu/releases/tag/v1.9.0",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "rank_score": 0.89,
        "confidence": 0.94,
        "impact": "Eliminates plaintext secret leaks in Terraform/OpenTofu state backends",
        "trust_badge": "primary",
        "badge": "primary",
        "install_command": "brew install opentofu",
        "install_commit": "34567890abcdef1234567890abcdef1234567890",
        "commit_sha": "34567890abcdef1234567890abcdef1234567890",
        "risk_flags": [],
        "seeded": True,
        "review_flag": False,
        "members": [
            {"article_id": "art-06", "url": "https://opentofu.org/announcements/v1.9.0", "title": "OpenTofu State Encryption", "publisher": "OpenTofu Foundation", "trust_tier": 1}
        ],
        "evidence": [
            {"evidence_url": "https://github.com/opentofu/opentofu/releases/tag/v1.9.0", "evidence_type": "primary_source", "source_reference": "OpenTofu GitHub Release", "status": "supported", "confidence": 0.98}
        ],
        "claims": [
            {"claim_id": "c-06", "claim_text": "State file encryption is configured natively in tofu block", "claim_type": "CAPABILITY", "status": "supported"}
        ],
    },
    {
        "_id": "story-cloud-003",
        "title": "Vector 0.42 Log Aggregator: Rust Memory Deallocation Regression",
        "summary": "Datadog team issues advisory regarding high buffer retention on high-cardinality JSON pipelines.",
        "room_key": "cloud",
        "topics": ["cloud"],
        "source_domain": "github.com",
        "source_url": "https://github.com/vectordotdev/vector/issues/21450",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "rank_score": 0.81,
        "confidence": 0.87,
        "impact": "Memory exhaustion vulnerability on high throughput log ingestion nodes",
        "trust_badge": "vendor_reported",
        "badge": "vendor_reported",
        "risk_flags": [],
        "seeded": True,
        "review_flag": False,
        "members": [
            {"article_id": "art-07", "url": "https://github.com/vectordotdev/vector/issues/21450", "title": "Vector Issue 21450", "publisher": "GitHub", "trust_tier": 2}
        ],
        "evidence": [
            {"evidence_url": "https://github.com/vectordotdev/vector/issues/21450", "evidence_type": "independent_reporting", "source_reference": "GitHub Issue Tracker triage", "status": "supported", "confidence": 0.90}
        ],
        "claims": [
            {"claim_id": "c-07", "claim_text": "Vector 0.42 causes memory leak under high-cardinality JSON sink workloads", "claim_type": "CAPABILITY", "status": "supported"}
        ],
    },
    {
        "_id": "story-cloud-004",
        "title": "Cilium 1.16: WireGuard Transparent Mesh Encryption in Kernel",
        "summary": "Cilium integrates transparent node-to-node WireGuard encryption directly inside eBPF data path.",
        "room_key": "cloud",
        "topics": ["cloud"],
        "source_domain": "isovalent.com",
        "source_url": "https://github.com/cilium/cilium/releases/tag/v1.16.0",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "rank_score": 0.87,
        "confidence": 0.93,
        "impact": "Zero-overhead secure overlay network for Kubernetes clusters",
        "trust_badge": "primary",
        "badge": "primary",
        "install_command": "helm install cilium cilium/cilium --version 1.16.0 --namespace kube-system",
        "install_commit": "567890abcdef1234567890abcdef1234567890ab",
        "commit_sha": "567890abcdef1234567890abcdef1234567890ab",
        "risk_flags": [],
        "seeded": True,
        "review_flag": False,
        "members": [
            {"article_id": "art-08", "url": "https://isovalent.com/blog/post/cilium-release-116", "title": "Cilium 1.16 Release", "publisher": "Isovalent", "trust_tier": 1}
        ],
        "evidence": [
            {"evidence_url": "https://github.com/cilium/cilium/releases/tag/v1.16.0", "evidence_type": "primary_source", "source_reference": "GitHub API releases", "status": "supported", "confidence": 0.97}
        ],
        "claims": [
            {"claim_id": "c-08", "claim_text": "WireGuard mesh encryption is enabled with encryption.type=wireguard", "claim_type": "CAPABILITY", "status": "supported"}
        ],
    },

    # --- SECURITY (4) ---
    {
        "_id": "story-sec-001",
        "title": "CVE-2026-4412: PyTorch Remote Code Execution via Malformed TorchScript Deserialization",
        "summary": "Critical severity CVSS 9.8 advisory published by PyTorch foundation affecting models loaded via torch.jit.load.",
        "room_key": "security",
        "topics": ["security", "cve"],
        "source_domain": "osv.dev",
        "source_url": "https://osv.dev/vulnerability/GHSA-4412-pytorch",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "rank_score": 0.98,
        "confidence": 0.99,
        "impact": "CRITICAL vulnerability: Arbitrary code execution during model checkpoint evaluation",
        "trust_badge": "primary",
        "badge": "primary",
        "entities": ["pytorch", "torchscript"],
        "risk_flags": ["critical_cve", "remote_code_execution"],
        "seeded": True,
        "review_flag": False,
        "members": [
            {"article_id": "art-09", "url": "https://osv.dev/vulnerability/GHSA-4412-pytorch", "title": "PyTorch Security Advisory", "publisher": "OSV Database", "trust_tier": 1}
        ],
        "evidence": [
            {"evidence_url": "https://osv.dev/vulnerability/GHSA-4412-pytorch", "evidence_type": "primary_source", "source_reference": "OSV API Security Advisory", "status": "supported", "confidence": 1.0}
        ],
        "claims": [
            {"claim_id": "c-09", "claim_text": "PyTorch versions prior to 2.4.1 contain CVSS 9.8 vulnerability", "claim_type": "SECURITY", "status": "supported"}
        ],
    },
    {
        "_id": "story-sec-002",
        "title": "Supply Chain Alert: Malicious Typosquatting in npm 'axios-auth-refresh-v2'",
        "summary": "Security researchers detect credential exfiltration payload targeting cloud environment variables in popular npm fork.",
        "room_key": "security",
        "topics": ["security"],
        "source_domain": "socket.dev",
        "source_url": "https://socket.dev/npm/package/axios-auth-refresh-v2",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "rank_score": 0.92,
        "confidence": 0.95,
        "impact": "Exfiltration of AWS and GitHub secrets via preinstall npm hooks",
        "trust_badge": "primary",
        "badge": "primary",
        "entities": ["axios-auth-refresh-v2"],
        "risk_flags": ["malware_package", "env_exfiltration"],
        "seeded": True,
        "review_flag": False,
        "members": [
            {"article_id": "art-10", "url": "https://socket.dev/npm/package/axios-auth-refresh-v2", "title": "Socket Security Alert", "publisher": "Socket Dev", "trust_tier": 1}
        ],
        "evidence": [
            {"evidence_url": "https://registry.npmjs.org/axios-auth-refresh-v2", "evidence_type": "primary_source", "source_reference": "npm Registry Security Advisory", "status": "supported", "confidence": 0.98}
        ],
        "claims": [
            {"claim_id": "c-10", "claim_text": "Package contains encoded shell script sending env to external IP", "claim_type": "SECURITY", "status": "supported"}
        ],
    },
    {
        "_id": "story-sec-003",
        "title": "Sigstore Fulcio 1.6.0: Ephemeral Certificate Validation Hardening",
        "summary": "Sigstore project releases critical update patching OIDC audience validation bypass in artifact signing flow.",
        "room_key": "security",
        "topics": ["security"],
        "source_domain": "sigstore.dev",
        "source_url": "https://github.com/sigstore/fulcio/releases/tag/v1.6.0",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "rank_score": 0.86,
        "confidence": 0.92,
        "impact": "Prevents unauthorized identity assertions on container image signatures",
        "trust_badge": "vendor_reported",
        "badge": "vendor_reported",
        "risk_flags": [],
        "seeded": True,
        "review_flag": False,
        "members": [
            {"article_id": "art-11", "url": "https://blog.sigstore.dev/fulcio-update", "title": "Sigstore Advisory", "publisher": "Sigstore Blog", "trust_tier": 2}
        ],
        "evidence": [
            {"evidence_url": "https://github.com/sigstore/fulcio/releases/tag/v1.6.0", "evidence_type": "primary_source", "source_reference": "GitHub Release Notes", "status": "supported", "confidence": 0.94}
        ],
        "claims": [
            {"claim_id": "c-11", "claim_text": "Fulcio v1.6.0 strictly verifies OIDC token audience matching", "claim_type": "SECURITY", "status": "supported"}
        ],
    },
    {
        "_id": "story-sec-004",
        "title": "TruffleHog v3.88: Autonomous Detection for Cloudflare Tunnel Credentials",
        "summary": "Open-source credential scanner adds zero-false-positive detector for Cloudflare Zero Trust tunnel tokens.",
        "room_key": "security",
        "topics": ["security"],
        "source_domain": "github.com",
        "source_url": "https://github.com/trufflesecurity/trufflehog/releases/tag/v3.88.0",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "rank_score": 0.88,
        "confidence": 0.94,
        "impact": "Proactive prevention of internal network ingress exposures",
        "trust_badge": "primary",
        "badge": "primary",
        "install_command": "brew install trufflehog",
        "install_commit": "7890abcdef1234567890abcdef1234567890abcdef",
        "commit_sha": "7890abcdef1234567890abcdef1234567890abcdef",
        "risk_flags": [],
        "seeded": True,
        "review_flag": False,
        "members": [
            {"article_id": "art-12", "url": "https://trufflesecurity.com/blog/cloudflare-detector", "title": "TruffleHog Release", "publisher": "Truffle Security", "trust_tier": 1}
        ],
        "evidence": [
            {"evidence_url": "https://github.com/trufflesecurity/trufflehog/releases/tag/v3.88.0", "evidence_type": "primary_source", "source_reference": "GitHub API release", "status": "supported", "confidence": 0.96}
        ],
        "claims": [
            {"claim_id": "c-12", "claim_text": "TruffleHog v3.88 verifies active Cloudflare tunnel tokens via live API probe", "claim_type": "CAPABILITY", "status": "supported"}
        ],
    },
]

INITIAL_RADAR = [
    {
        "_id": "radar-001",
        "room_key": "aiml",
        "title": "LitServe: High-throughput AI model serving with FastAPI engine",
        "url": "https://github.com/Lightning-AI/LitServe",
        "description": "Up to 50x faster than plain FastAPI for PyTorch, LLM and diffusion serving pipelines.",
        "topics": ["aiml", "llm"],
        "vote_count": 14,
        "submitted_by": "alice_aiml",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "radar-002",
        "room_key": "cloud",
        "title": "Karpenter: Kubernetes Just-In-Time Node Autoscaler",
        "url": "https://github.com/aws/karpenter-provider-aws",
        "description": "Flexible, ultra-fast node provisioning directly reacting to pending pods.",
        "topics": ["cloud", "kubernetes"],
        "vote_count": 19,
        "submitted_by": "bob_cloud",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "_id": "radar-003",
        "room_key": "security",
        "title": "Trivy: All-in-one container, filesystem and repo security scanner",
        "url": "https://github.com/aquasecurity/trivy",
        "description": "Fast vulnerability, misconfiguration and secret detection for CI/CD.",
        "topics": ["security"],
        "vote_count": 27,
        "submitted_by": "lead_reviewer",
        "created_at": datetime.now(timezone.utc).isoformat(),
    },
]



INITIAL_DIGESTS = [
    {
        "_id": "digest-aiml-001",
        "room_key": "aiml",
        "version": 1,
        "status": "review_required",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seeded": True,
        "items": [
            {"story_id": "story-aiml-001", "position": 0, "editor_note": "Speculative decoding breakthrough in vLLM", "included": True},
            {"story_id": "story-aiml-002", "position": 1, "editor_note": "Qwen 2.5 Coder benchmark verification", "included": True},
            {"story_id": "story-aiml-003", "position": 2, "editor_note": "Ollama tool calling enhancement", "included": True},
            {"story_id": "story-aiml-004", "position": 3, "editor_note": "FastAPI community signal on DSPy", "included": True},
        ],
        "approvals": [],
    },
    {
        "_id": "digest-cloud-001",
        "room_key": "cloud",
        "version": 1,
        "status": "review_required",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seeded": True,
        "items": [
            {"story_id": "story-cloud-001", "position": 0, "editor_note": "Kubernetes 1.32 DRA in-place pod resizing", "included": True},
            {"story_id": "story-cloud-002", "position": 1, "editor_note": "Terraform 1.10 ephemeral values for credentials", "included": True},
            {"story_id": "story-cloud-003", "position": 2, "editor_note": "Cilium 1.16 BGP and BIG-TCP throughput", "included": True},
            {"story_id": "story-cloud-004", "position": 3, "editor_note": "Vector pipeline buffer warning", "included": True},
        ],
        "approvals": [],
    },
    {
        "_id": "digest-sec-001",
        "room_key": "security",
        "version": 1,
        "status": "review_required",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seeded": True,
        "items": [
            {"story_id": "story-sec-001", "position": 0, "editor_note": "CRITICAL: requests CVE-2024-35195 redirect header leak", "included": True},
            {"story_id": "story-sec-002", "position": 1, "editor_note": "HIGH: PyYAML CVE-2024-5174 arbitrary code execution", "included": True},
            {"story_id": "story-sec-003", "position": 2, "editor_note": "HIGH: Sigstore cosign offline certificate verification", "included": True},
            {"story_id": "story-sec-004", "position": 3, "editor_note": "TruffleHog v3.88 zero-false-positive detector", "included": True},
        ],
        "approvals": [],
    },
]

async def seed_initial_data(db: AsyncIOMotorDatabase) -> None:
    """Inserts initial seed records idempotently using upserts."""
    logger.info("Checking and seeding initial NewsOps data...")

    # Seed rooms
    for room in INITIAL_ROOMS:
        await db.rooms.update_one({"key": room["key"]}, {"$set": room}, upsert=True)

    # Seed users
    for user in INITIAL_USERS:
        await db.users.update_one({"_id": user["_id"]}, {"$setOnInsert": user}, upsert=True)

    # Seed sources
    for source in INITIAL_SOURCES:
        await db.sources.update_one({"_id": source["_id"]}, {"$setOnInsert": source}, upsert=True)

    # When offline mode is enabled, seed realistic stories and radar items
    if settings.NEWSOPS_OFFLINE:
        logger.info(f"NEWSOPS_OFFLINE=True: Seeding {len(INITIAL_STORIES)} realistic stories across #aiml, #cloud, #security...")
        for story in INITIAL_STORIES:
            await db.stories.update_one({"_id": story["_id"]}, {"$set": story}, upsert=True)

        for item in INITIAL_RADAR:
            await db.radar_items.update_one({"_id": item["_id"]}, {"$setOnInsert": item}, upsert=True)

        for digest in INITIAL_DIGESTS:
            await db.digests.update_one({"_id": digest["_id"]}, {"$set": digest}, upsert=True)

    logger.info("Seed data verification completed.")
