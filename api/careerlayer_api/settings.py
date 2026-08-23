from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str

    # Seconds. A readiness probe that outlives the orchestrator's own probe timeout is
    # reported as a crashed container rather than as a dependency outage, which sends
    # whoever is on call to the wrong service.
    dependency_probe_timeout: float = 2.0

    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "careerlayer"
    s3_secret_key: str = "careerlayer-dev-secret"
    s3_bucket: str = "careerlayer-resumes"
    s3_region: str = "us-east-1"

    session_cookie_name: str = "careerlayer_session"
    session_ttl_hours: int = 24 * 14
    login_token_ttl_minutes: int = 15

    # Both caps are enforced before the file is stored or parsed further. A 20MB, 40-page
    # ceiling covers every real resume and bounds what one request can cost the worker.
    max_upload_bytes: int = 20 * 1024 * 1024
    max_page_count: int = 40

    render_dpi: int = 200

    # In development the sign-in link is returned in the response and written to the log so
    # the flow works with no mail server. Any other value withholds it, and a deployment that
    # forgets to set this fails closed rather than emailing itself.
    environment: str = "production"

    # Phase 3 LLM settings contract (sections 7.1 and 12.2)
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-5"
    llm_fallback_model: str = "claude-opus-5"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_inference_geo: str | None = None
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 1
    llm_temperature: float = 0.0
    llm_max_output_tokens_extraction: int = 4096
    llm_max_output_tokens_matching: int = 8192
    llm_cache_ttl: str = "5m"
    llm_data_processing_mode: str = "disabled"
    llm_privacy_attestation_id: str | None = None
    llm_privacy_verified_at: str | None = None

    @property
    def expose_login_links(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
