from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API keys
    gemini_api_keys: str = ""
    groq_api_keys:   str = ""

    # AI model names
    gemini_model: str = ""
    groq_model:   str = ""

    # Admin
    admin_secret:      str = ""
    admin_cookie_days: int = 30

    # Rate limiting
    rate_limit_per_day: int = 20

    # Public identity (non-secret, still env-driven)
    github_username: str = ""
    allowed_origin:  str = ""

    # Context encryption
    context_encryption_key: str = ""

    # Modal / SLM
    modal_endpoint:    str  = ""
    modal_enabled:     bool = True
    modal_volume_name: str  = ""
    modal_memory:      int  = 4096
    modal_timeout:     int  = 120
    slm_timeout:       int  = 90

    # HuggingFace model
    hf_repo_id:  str = ""
    hf_filename: str = ""

    # LLM inference params
    llm_n_ctx:      int   = 4096
    llm_n_threads:  int   = 4
    llm_max_tokens: int   = 512
    llm_temperature: float = 0.3

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
