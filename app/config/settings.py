from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    gemini_api_key: str
    redis_url: str = "redis://localhost:6379"
    config_path: str = "config.yaml"
    gateway_api_key: str = "dev-key"
    log_level: str = "INFO"
    environment: str = "development"
    prometheus_enabled: bool = True

    model_config = {"env_file": ".env"}
