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

    # Local dev/test default matches docker-compose.yml's postgres service at repo
    # root. Production points this at the real (private, VPC-only) RDS instance.
    database_url: str = "postgresql+psycopg2://aplit_grader:local_dev_only@localhost:5432/aplit_grader"

    # Not secrets — a Cognito user pool ID and app client ID are public identifiers
    # (the client here has no client secret, since it's called directly from the
    # frontend). Overridable via env for other environments/pools.
    cognito_region: str = "us-east-2"
    cognito_user_pool_id: str = "us-east-2_hZY5RNs81"
    cognito_app_client_id: str = "7amuvrc9l1sn727kqp6paraoqk"


@lru_cache
def get_settings() -> Settings:
    return Settings()
