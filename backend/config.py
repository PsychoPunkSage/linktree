from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str = ""
    groq_api_key: str = ""
    admin_secret: str = "changeme"
    rate_limit_per_day: int = 20
    github_username: str = "psychopunksage"
    allowed_origin: str = "https://psychopunksage.dev"

    class Config:
        env_file = ".env"

settings = Settings()
