
from functools import lru_cache

import boto3
import requests
from requests.adapters import HTTPAdapter
from supabase import Client, create_client
from urllib3.util.retry import Retry

from .config import AWSConfig, PipelineConfig, SupabaseConfig, get_settings


def create_http_session(config: PipelineConfig | None = None) -> requests.Session:
    if config is None:
        config = get_settings().pipeline

    session = requests.Session()
    retry_strategy = Retry(
        total=config.max_retries,
        backoff_factor=config.retry_backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


@lru_cache(maxsize=1)
def get_supabase_client(config: SupabaseConfig | None = None) -> Client:
    if config is None:
        config = get_settings().supabase
    return create_client(config.url, config.key)


def create_s3_client(config: AWSConfig | None = None):
    if config is None:
        config = get_settings().aws

    return boto3.client(
        "s3",
        region_name=config.region,
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
    )
