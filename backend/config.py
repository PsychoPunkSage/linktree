from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_keys: str = ""
    groq_api_keys:   str = ""
    admin_secret: str = "changeme"
    rate_limit_per_day: int = 20
    github_username: str = "psychopunksage"
    allowed_origin: str = "https://psychopunksage.dev"
    context_encryption_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
