"""Runtime configuration, loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Volvo developer app
    volvo_client_id: str = ""
    volvo_client_secret: str = ""
    volvo_vcc_api_key: str = ""
    volvo_redirect_uri: str = "http://localhost:8000/auth/callback"
    volvo_scopes: str = "openid"

    # Service
    public_base_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./data/volvowatch.db"
    fernet_key: str = ""
    device_token_pepper: str = ""
    status_cache_ttl: int = 60
    # www.tallimedia.com's feedback form POSTs here cross-origin.
    extra_allowed_origins: str = "https://www.tallimedia.com"

    # Feedback form (www.tallimedia.com's #contact section) — sent via SMTP,
    # not stored. All optional; the endpoint 503s if smtp_host is unset.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    feedback_to_email: str = "iot@tallimedia.com"

    # Optional: usable tank size, to derive a fuel % (Volvo only reports litres).
    # XC60 PHEV ~= 60 L usable. Leave 0 to omit fuel_pct.
    fuel_tank_litres: float = 0.0

    @property
    def scope_list(self) -> list[str]:
        return [s for s in self.volvo_scopes.split() if s]

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.extra_allowed_origins.split(",") if o.strip()]

    def require_volvo_credentials(self) -> None:
        missing = [
            name
            for name, value in {
                "VOLVO_CLIENT_ID": self.volvo_client_id,
                "VOLVO_CLIENT_SECRET": self.volvo_client_secret,
                "VOLVO_VCC_API_KEY": self.volvo_vcc_api_key,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing required Volvo credentials: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
