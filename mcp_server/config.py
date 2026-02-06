from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
import os


class MCPSettings(BaseSettings):
    # Azure Authentication
    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: str
    azure_subscription_id: str

    # Azure Resources
    azure_resource_group: str
    azure_data_factory_name: str
    azure_key_vault_name: str
    azure_storage_account_name: str

    # Terraform
    terraform_plans_dir: Path = Path("/app/infra/plans")

    # Application
    log_level: str = "INFO"
    log_file_path: Path = Path("/app/logs/mcp_server.log")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> MCPSettings:
    return MCPSettings()
