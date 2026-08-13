from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# ANTHROPIC_API_KEY isn't a Settings field below — the Anthropic SDK reads it
# directly from os.environ itself when AnthropicGradingClient doesn't pass an
# explicit api_key. pydantic-settings' env_file= only populates declared fields,
# so it never reaches os.environ on its own; load_dotenv() here does that.
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    grading_model_version: str = "claude-sonnet-5"
    result_logger_backend: Literal["local", "s3"] = "local"
    result_logger_local_dir: str = "./grading_results"
    s3_bucket: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
