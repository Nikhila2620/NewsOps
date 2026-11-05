"""
NewsOps Revision 2 - Topic Classification Pipeline.
Maps articles to taxonomy topics using keyword rules.
Topics: aiml, cloud, devtools, security, data, web_backend, oss
"""
import re
from typing import Dict, List, Tuple

TAXONOMY = {
    "aiml": [
        "llm", "language model", "gpt", "claude", "gemini", "openai", "anthropic",
        "hugging face", "transformers", "pytorch", "tensorflow", "neural network",
        "machine learning", "deep learning", "diffusion", "stable diffusion",
        "computer vision", "nlp", "natural language", "rag", "embedding", "vector",
        "inference", "fine-tun", "llamafile", "ollama", "mistral", "ai agent",
        "multimodal", "foundation model", "reinforcement learning",
    ],
    "cloud": [
        "kubernetes", "k8s", "docker", "container", "aws", "azure", "gcp",
        "google cloud", "amazon web", "serverless", "lambda", "cloud function",
        "terraform", "pulumi", "helm", "eks", "aks", "gke", "s3", "dynamodb",
        "cloudflare", "vercel", "netlify", "cdn", "infrastructure", "iaas", "paas",
    ],
    "security": [
        "cve", "vulnerability", "exploit", "patch", "security advisory", "ransomware",
        "malware", "phishing", "zero-day", "xss", "sql injection", "csrf", "supply chain",
        "sbom", "osv", "nvd", "nist", "pentest", "red team", "soc", "siem",
        "authentication", "oauth", "jwt", "encryption", "cryptograph", "tls", "ssl",
    ],
    "devtools": [
        "ide", "vscode", "neovim", "jetbrains", "copilot", "cursor", "codeium",
        "lsp", "debugger", "profiler", "linter", "formatter", "eslint", "prettier",
        "build tool", "webpack", "vite", "esbuild", "bazel", "cargo", "gradle",
        "ci/cd", "github actions", "gitlab ci", "jenkins", "developer experience", "dx",
    ],
    "data": [
        "database", "postgresql", "mysql", "sqlite", "redis", "mongodb", "cassandra",
        "clickhouse", "duckdb", "data pipeline", "etl", "kafka", "spark", "airflow",
        "dbt", "snowflake", "bigquery", "data warehouse", "data lake", "analytics",
        "pandas", "polars", "arrow", "parquet", "olap",
    ],
    "web_backend": [
        "fastapi", "django", "flask", "express", "node.js", "rust", "go", "golang",
        "api", "rest", "graphql", "grpc", "websocket", "microservice", "monolith",
        "spring", "rails", "laravel", "asp.net", "bun", "deno", "http", "proxy",
        "load balancer", "nginx", "caddy", "traefik",
    ],
    "oss": [
        "open source", "open-source", "github", "gitlab", "git", "license", "mit license",
        "apache license", "gpl", "bsd", "fork", "pull request", "merge", "release",
        "maintainer", "contributor", "community", "hacktoberfest", "cncf",
    ],
}


def classify_topics(title: str, text: str = "", existing_topics: List[str] = None) -> Tuple[List[str], float]:
    """
    Classify article into taxonomy topics using keyword matching.
    Returns (topics_list, confidence_score).
    """
    if existing_topics is None:
        existing_topics = []
    
    combined = f"{title} {text}".lower()
    scores: Dict[str, int] = {}
    
    for topic, keywords in TAXONOMY.items():
        hits = sum(1 for kw in keywords if re.search(re.escape(kw), combined))
        if hits > 0:
            scores[topic] = hits
    
    if not scores:
        # Fall back to existing topics or "oss" as catch-all
        return existing_topics or ["oss"], 0.3
    
    # Sort by hits descending
    sorted_topics = sorted(scores, key=scores.__getitem__, reverse=True)
    top_hits = scores[sorted_topics[0]]
    
    # Include topics with >= 50% of top score
    selected = [t for t in sorted_topics if scores[t] >= max(1, top_hits * 0.5)]
    
    # Confidence: scale 0.5-1.0 based on top hits
    confidence = min(1.0, 0.5 + (top_hits / 10.0))
    
    # Merge with existing topics (preserve any manually set ones)
    merged = list(dict.fromkeys(selected + existing_topics))
    return merged[:5], confidence  # cap at 5 topics
