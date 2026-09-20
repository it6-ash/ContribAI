from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Sentinel so the production guard can recognise "nobody set this".
DEV_SECRET = "dev-only-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "development" seeds the demo corpus and enables demo sign-in.
    # "production" does neither, and refuses to boot on a default secret.
    # One knob instead of three flags that can disagree with each other.
    environment: str = "development"

    # ponytail: sqlite by default so the demo runs with zero infra.
    # Point DATABASE_URL at postgres for a real deployment; SQLAlchemy handles the rest.
    database_url: str = "sqlite:///./contribai.db"

    session_secret: str = DEV_SECRET
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    github_client_id: str = ""
    github_client_secret: str = ""
    # Server-side PAT used for unauthenticated issue discovery (raises the 60/hr limit to 5000/hr).
    github_token: str = ""

    # Groq (OpenAI-compatible endpoint). gpt-oss-120b is the strongest general
    # reasoning model Groq serves; the 20b is the cheap fallback if latency bites.
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_reasoning_effort: str = "medium"  # gpt-oss only: low | medium | high

    # Shared secret for POST /api/ingest/issues. The scheduled refresh no longer
    # needs this; it is kept for pushing a curated corpus from a script or CI.
    # Empty disables the endpoint entirely rather than leaving it open.
    ingest_token: str = ""

    # --- built-in corpus refresh -------------------------------------------
    # Replaces the external scheduler. Needs GITHUB_TOKEN; without one the
    # anonymous 60 req/hr budget is gone in a single tick, so it stays idle.
    corpus_refresh_enabled: bool = True
    refresh_interval_minutes: int = 360
    refresh_languages: str = "python,typescript,go"
    refresh_startup_delay_seconds: int = 30

    # Hard cap on issues pulled per discovery run, keeps demo latency predictable.
    max_candidate_issues: int = 150

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    def check(self) -> None:
        """Fail at boot rather than serving something unsafe.

        A default SESSION_SECRET means anyone can forge a session cookie for any
        user id, and it is also the key wrapping stored GitHub tokens.
        """
        if self.is_production and self.session_secret == DEV_SECRET:
            raise RuntimeError(
                "SESSION_SECRET is still the development default. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
