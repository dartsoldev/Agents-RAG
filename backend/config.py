"""Load and validate server-side configuration without exposing secret values."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    app_url: str = "http://127.0.0.1:8000"
    database_url: str = "sqlite:///./data/arav.db"
    storage_path: str = "./data/documents"
    demo_mode: bool = True
    seed_demo: bool = True
    admin_email: str = "admin@arav.local"
    admin_password: str = "ChangeMe-Demo-2026!"
    cookie_secure: bool = False
    ai_provider: str = "demo"
    openai_api_key: str = ""
    openai_model: str = "gpt-6-astra"
    embeddings_enabled: bool = False
    openai_embedding_model: str = "text-embedding-3-small"
    worker_enabled: bool = True
    monitor_interval_seconds: int = 3600
    medical_gap_days: int = 14
    insurance_gap_days: int = 10
    max_upload_mb: int = 20
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    filevine_base_url: str = "https://api.filevineapp.com"
    filevine_access_token: str = ""
    filevine_org_id: str = ""
    filevine_user_id: str = ""
    filevine_project_type_id: str = ""

    def validate_runtime(self):
        if self.ai_provider not in {"demo", "openai"}:
            raise ValueError("AI_PROVIDER must be demo or openai")
        if (self.ai_provider == "openai" or self.embeddings_enabled) and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for the selected AI configuration")
        if self.demo_mode and (self.ai_provider != "demo" or self.embeddings_enabled):
            raise ValueError("Turn DEMO_MODE off before enabling external AI")
        if not self.demo_mode and (self.seed_demo or self.admin_password == "ChangeMe-Demo-2026!"):
            raise ValueError("Real mode requires SEED_DEMO=false and a new ADMIN_PASSWORD")
        if self.app_env == "production":
            if self.demo_mode or not self.cookie_secure or not self.app_url.startswith("https://"):
                raise ValueError("Production requires real mode, HTTPS and secure cookies")
            if len(self.admin_password) < 16 or self.database_url.startswith("sqlite"):
                raise ValueError(
                    "Production requires PostgreSQL and a 16+ character admin password"
                )
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        Path("data").mkdir(exist_ok=True)


settings = Settings()
