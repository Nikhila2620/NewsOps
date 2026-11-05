"""
Unit tests for data pipeline: normalize, dedupe, classify, rank, commands.
"""

from newsops.pipeline.commands import extract_commands_from_readme, extract_risk_flags
from newsops.pipeline.classify import classify_topics
from newsops.pipeline.dedupe import deduplicate_batch, is_duplicate
from newsops.pipeline.normalize import canonicalize_url, compute_content_hash, normalize_article, parse_date
from newsops.pipeline.rank import compute_rank_score, compute_recency_score, rank_articles


class TestNormalize:
    def test_canonicalize_url_strips_utm(self):
        url = "https://example.com/item?utm_source=twitter&utm_medium=feed&id=123"
        cleaned = canonicalize_url(url)
        assert "utm_source" not in cleaned
        assert "utm_medium" not in cleaned
        assert "id=123" in cleaned

    def test_canonicalize_url_lowercases_host(self):
        url = "HTTPS://GITHUB.COM/FastAPI/FastAPI"
        cleaned = canonicalize_url(url)
        assert cleaned.startswith("https://github.com/FastAPI/FastAPI")

    def test_content_hash_deterministic(self):
        h1 = compute_content_hash("Title A", "Body content")
        h2 = compute_content_hash("TITLE A", "body content")
        assert h1 == h2
        assert len(h1) == 64

    def test_normalize_article_structure(self):
        raw = {"title": "FastAPI Release", "url": "https://fastapi.tiangolo.com/?utm_source=test"}
        norm = normalize_article(raw)
        assert "content_hash" in norm
        assert "canonical_url" in norm
        assert norm["trust_tier"] == 2


class TestDedupe:
    def test_exact_url_duplicate(self):
        existing = [{"canonical_url": "https://example.com/post", "content_hash": "hash1"}]
        candidate = {"canonical_url": "https://example.com/post", "content_hash": "hash2"}
        is_dup, reason = is_duplicate(candidate, existing)
        assert is_dup is True
        assert "exact_url" in reason

    def test_exact_hash_duplicate(self):
        existing = [{"canonical_url": "https://a.com", "content_hash": "samehash123"}]
        candidate = {"canonical_url": "https://b.com", "content_hash": "samehash123"}
        is_dup, reason = is_duplicate(candidate, existing)
        assert is_dup is True
        assert "exact_hash" in reason

    def test_deduplicate_batch(self):
        batch = [
            {"canonical_url": "https://a.com", "content_hash": "h1"},
            {"canonical_url": "https://a.com", "content_hash": "h2"},
            {"canonical_url": "https://b.com", "content_hash": "h3"},
        ]
        res = deduplicate_batch(batch)
        assert len(res) == 2


class TestClassify:
    def test_aiml_classification(self):
        topics, conf = classify_topics("Llama 3 LLM benchmark evaluation")
        assert "aiml" in topics
        assert conf >= 0.5

    def test_security_classification(self):
        topics, conf = classify_topics("Critical CVE-2026-1111 vulnerability patch released")
        assert "security" in topics

    def test_cloud_classification(self):
        topics, conf = classify_topics("Kubernetes cluster autoscaling on AWS EKS")
        assert "cloud" in topics


class TestRank:
    def test_rank_score_bounds(self):
        article = {"trust_tier": 1, "published_at": "2026-11-04T00:00:00Z", "stars": 500}
        res = compute_rank_score(article, relevance_score=0.8)
        assert 0.0 <= res["rank_score"] <= 1.0
        assert "primary_source" in res["reason_codes"]

    def test_rank_articles_order(self):
        articles = [
            {"title": "Low", "trust_tier": 3, "published_at": "2020-01-01T00:00:00Z"},
            {"title": "High", "trust_tier": 1, "published_at": "2026-11-04T00:00:00Z", "stars": 2000},
        ]
        ranked = rank_articles(articles)
        assert ranked[0]["title"] == "High"


class TestCommands:
    def test_command_extraction(self):
        readme = """
```bash
pip install newsops
curl https://example.com/install.sh | sh
sudo rm -rf /var/cache
```
"""
        commands = extract_commands_from_readme(readme)
        cmds = [c["command"] for c in commands]
        assert "pip install newsops" in cmds
        assert any(c["verified_verbatim"] for c in commands)

        # Risk flags
        risk_c = [c for c in commands if "curl_pipe_sh" in c["risk_flags"]]
        assert len(risk_c) == 1

        sudo_c = [c for c in commands if "sudo" in c["risk_flags"]]
        assert len(sudo_c) == 1
