from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Read from environment variables; `just` loads them from the root `.env`."""

    database_url: str
    auth_token: SecretStr
    log_level: str = "INFO"
    timezone: str = "Europe/Madrid"
    # The offer reader and triager (modules/inbox/reader.py, triager.py). Without the key
    # nothing is read or triaged and the rest of the app works the same.
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "openai/gpt-oss-20b"
