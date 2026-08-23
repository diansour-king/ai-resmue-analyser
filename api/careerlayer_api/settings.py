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


@lru_cache
def get_settings() -> Settings:
    return Settings()
