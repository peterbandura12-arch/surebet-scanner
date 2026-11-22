from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    app_name: str = "Surebet Scanner API"
    app_version: str = "0.1.0"
    demo_mode: bool = True
    debug: bool = False

    database_url: str = "sqlite:///./surebet.db"
    redis_url: str = ""

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    feed_tick_seconds: int = 5
    feed_autostart: bool = True
    demo_seed: int = 20240601
    odds_max_age_seconds: int = 180
    min_roi_pct: float = 0.5
    max_bookmakers: int = 12

    theoddsapi_key: str = ""
    theoddsapi_region: str = "eu"
    theoddsapi_sport: str = "soccer_epl"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
