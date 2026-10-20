from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='GEOAI_', extra='ignore')

    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'
    commercial_source: str | None = None
    territorial_source: str | None = None
    output_dir: str = 'data/processed'


@lru_cache
def get_settings() -> Settings:
    return Settings()
