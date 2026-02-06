from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.keyvault.secrets import SecretClient
from azure.mgmt.resource import ResourceManagementClient
from functools import lru_cache
from mcp_server.config import get_settings


class AzureClientFactory:
    def __init__(self):
        self.settings = get_settings()
        self._credential = None

    @property
    def credential(self):
        """Get Azure credential (cached)"""
        if self._credential is None:
            if self.settings.azure_client_id and self.settings.azure_client_secret:
                self._credential = ClientSecretCredential(
                    tenant_id=self.settings.azure_tenant_id,
                    client_id=self.settings.azure_client_id,
                    client_secret=self.settings.azure_client_secret
                )
            else:
                self._credential = DefaultAzureCredential()
        return self._credential

    @lru_cache()
    def get_datafactory_client(self) -> DataFactoryManagementClient:
        """Get Data Factory management client"""
        return DataFactoryManagementClient(
            credential=self.credential,
            subscription_id=self.settings.azure_subscription_id
        )

    @lru_cache()
    def get_keyvault_client(self) -> SecretClient:
        """Get Key Vault secret client"""
        vault_url = f"https://{self.settings.azure_key_vault_name}.vault.azure.net"
        return SecretClient(
            vault_url=vault_url,
            credential=self.credential
        )

    @lru_cache()
    def get_resource_client(self) -> ResourceManagementClient:
        """Get Resource management client"""
        return ResourceManagementClient(
            credential=self.credential,
            subscription_id=self.settings.azure_subscription_id
        )


# Global instance
azure_clients = AzureClientFactory()
