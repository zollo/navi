"""Application settings, loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

# Placeholder signing keys shipped in examples; refused in production.
_PLACEHOLDER_SECRETS = {
    "",
    "change-me",
    "change-me-to-a-long-random-string",
    "CHANGE_ME_openssl_rand_hex_32",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    env: str = Field(default="development", alias="NAVI_ENV")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    # Public URL people reach Navi on; used to build shareable page links.
    public_url: str = Field(default="http://localhost:8080", alias="NAVI_PUBLIC_URL")

    # Build metadata (baked into the image at build time)
    app_version: str = Field(default="dev", alias="NAVI_VERSION")
    git_commit: str = Field(default="unknown", alias="NAVI_GIT_COMMIT")
    build_time: str = Field(default="unknown", alias="NAVI_BUILD_TIME")

    # Database
    postgres_user: str = Field(default="navi", alias="POSTGRES_USER")
    postgres_password: str = Field(default="navi", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="navi", alias="POSTGRES_DB")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")
    # Open a fresh connection per session instead of pooling (tests; always on for SQLite).
    db_null_pool: bool = Field(default=False, alias="DB_NULL_POOL")

    # Auth
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    # Let anyone create an account (and so a page) from the sign-up page.
    allow_registration: bool = Field(default=True, alias="ALLOW_REGISTRATION")

    # Let signed-in users import a page from Linktree (the API fetches linktr.ee).
    linktree_import_enabled: bool = Field(default=True, alias="LINKTREE_IMPORT_ENABLED")

    # Uploads (avatars)
    max_avatar_kb: int = Field(default=1024, alias="MAX_AVATAR_KB")

    # Custom domains (www.example.com showing a page). Off by default: serving them
    # needs DNS + TLS for hosts Navi doesn't own (see charts/navi customDomains).
    custom_domains_enabled: bool = Field(default=False, alias="CUSTOM_DOMAINS_ENABLED")
    # Hostname users point a CNAME at. Defaults to NAVI_PUBLIC_URL's host.
    custom_domain_target: str = Field(default="", alias="CUSTOM_DOMAIN_TARGET")
    # Comma-separated IPv4 addresses for apex domains (which can't use a CNAME).
    # Defaults to whatever the target resolves to.
    custom_domain_ips: str = Field(default="", alias="CUSTOM_DOMAIN_IPS")
    # Public resolvers used for verification, so split-horizon DNS inside the
    # cluster or LAN can't skew the answer. Empty = the system resolver.
    custom_domain_resolvers: str = Field(default="1.1.1.1,8.8.8.8", alias="CUSTOM_DOMAIN_RESOLVERS")
    # Comma-separated domains nobody may claim (they and their subdomains), e.g. your
    # own zone. The public URL's host and the CNAME target are always blocked.
    custom_domain_blocked: str = Field(default="", alias="CUSTOM_DOMAIN_BLOCKED")

    @model_validator(mode="after")
    def _require_real_secret(self) -> Settings:
        if self.env == "production" and self.secret_key.strip() in _PLACEHOLDER_SECRETS:
            raise ValueError("SECRET_KEY must be set to a random value in production")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Async SQLAlchemy URL used by the app."""
        if self.database_url_override:
            return self.database_url_override
        # URL.create escapes credentials, so passwords may contain @, : or /.
        return URL.create(
            "postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        """Sync URL used by Alembic migrations."""
        return self.database_url.replace("+asyncpg", "+psycopg2")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_avatar_bytes(self) -> int:
        return self.max_avatar_kb * 1024

    @property
    def public_host(self) -> str:
        return (urlsplit(self.public_url).hostname or "").lower()

    @property
    def custom_domain_cname_target(self) -> str:
        return (self.custom_domain_target.strip().rstrip(".") or self.public_host).lower()

    @property
    def custom_domain_ip_list(self) -> list[str]:
        return _split(self.custom_domain_ips)

    @property
    def custom_domain_resolver_list(self) -> list[str]:
        return _split(self.custom_domain_resolvers)

    @property
    def custom_domain_blocked_list(self) -> list[str]:
        blocked = [d.lower().strip(".") for d in _split(self.custom_domain_blocked)]
        host = self.public_host
        if host and host != "localhost":
            blocked.append(host)
        target = self.custom_domain_cname_target
        if target and target != "localhost":
            blocked.append(target)
        return sorted(set(blocked))


def _split(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
