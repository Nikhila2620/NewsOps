"""
NewsOps Revision 2 - Application Settings & Environment Variable Validation.

Uses Pydantic Settings v2 to validate configuration, secure secrets, and
enforce operational bounds specified in Revision 2 Section 11.
"""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central settings configuration with strict validation.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        str_strip_whitespace=True,
    )

    # Core Application
    APP_NAME: str = Field(default="NewsOps", description="Service application name")
    APP_ENV: str = Field(default="dev", description="Runtime environment: dev, test, staging, prod")
    API_HOST: str = Field(default="0.0.0.0", description="FastAPI bind address")
    API_PORT: int = Field(default=8000, ge=1, le=65535, description="FastAPI listen port")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 routing prefix")
    LOG_LEVEL: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")

    # Security & Tokens (Secrets are masked in representations)
    SESSION_SECRET: str = Field(
        default="dev-session-secret-must-be-changed-in-production-32-chars-long",
        min_length=16,
        description="Session encryption secret",
    )
    AGENT_API_TOKEN: str = Field(
        default="dev-agent-secret-token-change-me",
        min_length=8,
        description="Shared secret bearer token used by Switch template agents to authenticate against /agent/*",
    )
    NEWSOPS_API: str = Field(
        default="http://localhost:8000/api/v1",
        description="Full URL path to NewsOps API for CLI wrapper",
    )

    # Database (MongoDB 7)
    MONGODB_URI: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI string",
    )
    MONGODB_DB: str = Field(
        default="newsops",
        description="Primary database name",
    )
    MONGODB_TIMEOUT_MS: int = Field(
        default=5000,
        ge=500,
        le=30000,
        description="Server selection and socket timeout in milliseconds",
    )

    # Task Budgets & Safety Limits
    TASK_MAX_ARTICLES: int = Field(
        default=60,
        ge=1,
        le=500,
        description="Maximum articles retrieved per ingestion run",
    )
    TASK_MAX_COST_USD: float = Field(
        default=0.50,
        ge=0.0,
        le=50.0,
        description="Cost budget limit per digest run",
    )

    # SSRF Protection Allow-list
    ALLOWED_FETCH_DOMAINS: List[str] = Field(
        default=[
            "github.com",
            "api.github.com",
            "news.ycombinator.com",
            "hn.algolia.com",
            "oauth.reddit.com",
            "dev.to",
            "export.arxiv.org",
            "api.osv.dev",
            "pypi.org",
            "registry.npmjs.org",
        ],
        description="Domains permitted for external HTTP fetching",
    )

    # Optional External Service Credentials
    GITHUB_OAUTH_CLIENT_ID: Optional[str] = None
    GITHUB_OAUTH_CLIENT_SECRET: Optional[str] = None
    GITHUB_API_TOKEN: Optional[str] = None
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "newsops/0.1 (contact: dev@example.com)"
    PRODUCTHUNT_TOKEN: Optional[str] = None

    # Optional Fallback LLM Credentials (Analyst agent is primary in Revision 2)
    LLM_PROVIDER: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: Optional[str] = None

    # Switch Integration (optional poster)
    SWITCH_BASE_URL: Optional[str] = None
    SWITCH_POSTER_AGENT_ID: Optional[str] = None
    SWITCH_POSTER_TOKEN: Optional[str] = None

    @field_validator("ALLOWED_FETCH_DOMAINS", mode="before")
    @classmethod
    def parse_allowed_domains(cls, v):
        if isinstance(v, str):
            return [d.strip() for d in v.split(",") if d.strip()]
        return v

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        valid_envs = {"dev", "test", "staging", "prod", "production"}
        lowered = v.lower()
        if lowered not in valid_envs:
            raise ValueError(f"APP_ENV must be one of {valid_envs}, got '{v}'")
        return lowered


# Singleton settings instance
settings = Settings()
