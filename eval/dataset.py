"""
NewsOps Revision 2 - AI Evaluation Dataset and Benchmark Runner.

Evaluates Topic Classification accuracy and Vulnerability Detection precision/recall/F1.
"""

from typing import Any, Dict, List

EVAL_DATASET: List[Dict[str, Any]] = [
    {
        "id": "eval-001",
        "title": "GPT-5 sets new SOTA on reasoning benchmarks",
        "text": "OpenAI's GPT-5 achieves state-of-the-art results on MMLU and HumanEval benchmarks.",
        "expected_topics": ["aiml"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-002",
        "title": "Critical CVE-2026-9876 vulnerability in OpenSSL 3.x",
        "text": "A remote code execution vulnerability was found. Patch immediately.",
        "expected_topics": ["security"],
        "expected_vulnerability": True,
    },
    {
        "id": "eval-003",
        "title": "Kubernetes 1.31 released with improved scheduling",
        "text": "CNCF releases Kubernetes 1.31 with enhanced autoscaler and improved pod scheduling.",
        "expected_topics": ["cloud"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-004",
        "title": "New Rust framework is 5x faster than existing alternatives",
        "text": "Benchmarks show 5x performance improvement in throughput and latency reduction.",
        "expected_topics": ["web_backend"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-005",
        "title": "PostgreSQL 17 adds logical replication improvements",
        "text": "PostgreSQL 17 ships new features for logical replication and performance.",
        "expected_topics": ["data"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-006",
        "title": "VS Code 2.0 ships AI-powered code completion",
        "text": "Microsoft ships VS Code 2.0 with native LLM code completion integration.",
        "expected_topics": ["devtools", "aiml"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-007",
        "title": "npm supply chain attack targets popular lodash fork",
        "text": "Malicious package published mimicking lodash, stealing env vars.",
        "expected_topics": ["security", "oss"],
        "expected_vulnerability": True,
    },
    {
        "id": "eval-008",
        "title": "Llama 4 open-sourced under Apache 2.0 license",
        "text": "Meta releases Llama 4 weights as open source under Apache 2.0.",
        "expected_topics": ["aiml", "oss"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-009",
        "title": "AWS Lambda cold start reduced by 40% in new runtime",
        "text": "AWS announces Lambda cold start improvements of 40% in Node.js 22 runtime.",
        "expected_topics": ["cloud"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-010",
        "title": "FastAPI 1.0 stable release announced",
        "text": "Sebastián Ramírez announces FastAPI 1.0 stable with breaking changes.",
        "expected_topics": ["web_backend"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-011",
        "title": "XSS vulnerability found in popular React component library",
        "text": "Security researchers found XSS via unsanitized prop injection in react-modal.",
        "expected_topics": ["security", "web_backend"],
        "expected_vulnerability": True,
    },
    {
        "id": "eval-012",
        "title": "DuckDB adds native Iceberg support",
        "text": "DuckDB 1.2 ships native Apache Iceberg table format support.",
        "expected_topics": ["data"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-013",
        "title": "Mistral releases new 7B model outperforming GPT-4",
        "text": "Mistral AI releases a 7B parameter model that outperforms GPT-4 on coding tasks.",
        "expected_topics": ["aiml"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-014",
        "title": "GitHub Copilot now supports 20 more languages",
        "text": "GitHub Copilot adds support for 20 additional programming languages.",
        "expected_topics": ["devtools", "aiml"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-015",
        "title": "Terraform 2.0 breaks backward compatibility",
        "text": "HashiCorp Terraform 2.0 introduces breaking changes in state file format.",
        "expected_topics": ["cloud", "devtools"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-016",
        "title": "Redis fork Valkey hits 1.0 stable",
        "text": "Valkey, the Linux Foundation fork of Redis, releases 1.0 stable version.",
        "expected_topics": ["data", "oss"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-017",
        "title": "curl|sh installer found backdoored in popular devtool",
        "text": "A popular devtool install script contains a backdoor executed via curl|sh.",
        "expected_topics": ["security", "devtools"],
        "expected_vulnerability": True,
    },
    {
        "id": "eval-018",
        "title": "Apache Kafka 4.0 removes Zookeeper dependency",
        "text": "Kafka 4.0 completes KRaft migration, fully removing ZooKeeper requirement.",
        "expected_topics": ["data"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-019",
        "title": "Cloudflare Workers now supports Python",
        "text": "Cloudflare announces Python support for Workers edge runtime.",
        "expected_topics": ["cloud", "web_backend"],
        "expected_vulnerability": False,
    },
    {
        "id": "eval-020",
        "title": "Critical SQL injection in popular ORM affects 50k+ projects",
        "text": "CVE-2026-5555 SQL injection in SQLAlchemy filter() affects >50k GitHub projects.",
        "expected_topics": ["security", "data"],
        "expected_vulnerability": True,
    },
]


def run_evaluation() -> dict:
    from ..ai.classifier import classify_article
    from ..ai.claim_extractor import extract_claims
    from ..contracts.enums import ClaimType

    topic_correct = 0
    total = len(EVAL_DATASET)
    v_tp = v_fp = v_tn = v_fn = 0

    for item in EVAL_DATASET:
        cls_res = classify_article(item["title"], item["text"])
        predicted = set(cls_res["topics"])
        expected = set(item["expected_topics"])
        if predicted & expected:
            topic_correct += 1

        claims = extract_claims(item["title"], item["text"], item["id"])
        pred_vuln = any(c.claim_type == ClaimType.SECURITY for c in claims)
        exp_vuln = item["expected_vulnerability"]

        if pred_vuln and exp_vuln:
            v_tp += 1
        elif pred_vuln and not exp_vuln:
            v_fp += 1
        elif not pred_vuln and not exp_vuln:
            v_tn += 1
        else:
            v_fn += 1

    topic_accuracy = topic_correct / total
    precision = v_tp / (v_tp + v_fp) if (v_tp + v_fp) > 0 else 0.0
    recall = v_tp / (v_tp + v_fn) if (v_tp + v_fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "total_samples": total,
        "topic_accuracy": round(topic_accuracy, 4),
        "vulnerability_precision": round(precision, 4),
        "vulnerability_recall": round(recall, 4),
        "vulnerability_f1": round(f1, 4),
        "true_positives": v_tp,
        "false_positives": v_fp,
        "true_negatives": v_tn,
        "false_negatives": v_fn,
    }


if __name__ == "__main__":
    metrics = run_evaluation()
    print("NewsOps AI Evaluation Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
