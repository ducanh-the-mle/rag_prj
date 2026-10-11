from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "rag-data"


settings = Settings()