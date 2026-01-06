from dataclasses import dataclass, field
from functools import lru_cache

from decouple import config


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    key: str


@dataclass(frozen=True)
class AWSConfig:
    region: str
    bucket_name: str
    access_key_id: str
    secret_access_key: str


@dataclass(frozen=True)
class PipelineConfig:
    batch_size: int = 500
    max_workers: int = 10
    max_retries: int = 3
    retry_backoff: float = 1.0
    image_batch_size: int = 100
    translation_languages: tuple[str, ...] = ("pt",)


@dataclass(frozen=True)
class APIConfig:
    ygoprodeck_base_url: str = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
    ygoprodeck_image_template: str = "https://images.ygoprodeck.com/images/cards/{card_id}.jpg"


@dataclass(frozen=True)
class Settings:
    supabase: SupabaseConfig
    aws: AWSConfig
    pipeline: PipelineConfig
    api: APIConfig


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        supabase=SupabaseConfig(
            url=config("SUPABASE_DB_URL"),
            key=config("SUPABASE_DB_KEY"),
        ),
        aws=AWSConfig(
            region=config("AWS_REGION"),
            bucket_name=config("AWS_BUCKET_NAME"),
            access_key_id=config("AWS_ACCESS_KEY_ID"),
            secret_access_key=config("AWS_SECRET_ACCESS_KEY"),
        ),
        pipeline=PipelineConfig(),
        api=APIConfig(),
    )
