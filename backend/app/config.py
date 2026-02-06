from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Azure Authentication
    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: str
    azure_subscription_id: str

    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment_name: str
    azure_openai_api_version: str = "2024-02-15-preview"

    # MCP Server - use Docker service name in Docker environment
    mcp_server_url: str = "http://mcp-server:8001"

    # Application
    environment: str = "dev"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
