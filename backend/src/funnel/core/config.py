from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Read from environment variables; `just` loads them from the root `.env`."""

    database_url: str
    auth_token: SecretStr
    log_level: str = "INFO"
