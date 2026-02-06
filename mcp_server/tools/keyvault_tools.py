from typing import List, Dict, Any
from datetime import datetime
from mcp_server.utils.azure_client import azure_clients
from mcp_server.models.tool_schemas import (
    GetKeyVaultSecretsInput, GetKeyVaultSecretsOutput, SecretInfo,
    GetSecretUsageInput, GetSecretUsageOutput, SecretUsage
)
from mcp_server.config import get_settings
from mcp_server.tools.adf_tools import ADFTools
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class KeyVaultTools:
    """Azure Key Vault tools implementation"""

    def __init__(self):
        self.kv_client = azure_clients.get_keyvault_client()
        self.adf_tools = ADFTools()

    def get_keyvault_secrets(self, input_data: GetKeyVaultSecretsInput) -> GetKeyVaultSecretsOutput:
        """
        List secrets from Key Vault with metadata.

        Implementation:
        1. List all secrets from Key Vault
        2. Filter by prefix if specified
        3. Get secret properties (enabled, dates, tags)
        4. Determine risk level from tags or naming convention
        """
        try:
            logger.info("Fetching Key Vault secrets")
            secrets_list = []

            # List all secret properties
            secret_properties = self.kv_client.list_properties_of_secrets()

            for secret_prop in secret_properties:
                # Apply prefix filter
                if input_data.prefix and not secret_prop.name.startswith(input_data.prefix):
                    continue

                # Determine risk level
                risk_level = None
                if secret_prop.tags:
                    risk_level = secret_prop.tags.get('risk', None)

                # Check naming convention for risk
                if not risk_level:
                    if 'prod' in secret_prop.name.lower():
                        risk_level = 'high'
                    elif 'high-risk' in secret_prop.name.lower():
                        risk_level = 'high'
                    else:
                        risk_level = 'medium'

                # Filter by risk if needed
                if not input_data.include_high_risk and risk_level == 'high':
                    continue

                secrets_list.append(SecretInfo(
                    name=secret_prop.name,
                    enabled=secret_prop.enabled,
                    created_on=secret_prop.created_on,
                    updated_on=secret_prop.updated_on,
                    tags=secret_prop.tags or {},
                    risk_level=risk_level
                ))

            return GetKeyVaultSecretsOutput(
                secrets=secrets_list,
                total_count=len(secrets_list)
            )

        except Exception as e:
            logger.error(f"Error fetching Key Vault secrets: {str(e)}")
            raise

    def get_secret_usage(self, input_data: GetSecretUsageInput) -> GetSecretUsageOutput:
        """
        Find which pipelines and linked services use a specific secret.

        Implementation:
        1. Get all pipelines from ADF
        2. For each pipeline, get linked services
        3. For each linked service, check if it references the secret
        4. Determine if pipeline is production-critical
        """
        try:
            logger.info(f"Analyzing usage for secret: {input_data.secret_name}")

            df_client = azure_clients.get_datafactory_client()
            resource_group = settings.azure_resource_group
            factory_name = settings.azure_data_factory_name

            usages = []

            # Get all linked services
            linked_services = list(df_client.linked_services.list_by_factory(
                resource_group_name=resource_group,
                factory_name=factory_name
            ))

            # Map linked services that use this secret
            ls_using_secret = {}
            for ls in linked_services:
                uses_secret = False

                # Check type properties for Key Vault reference
                if hasattr(ls, 'type_properties'):
                    props_str = str(ls.type_properties)
                    # Check if this secret name appears in properties
                    if input_data.secret_name in props_str:
                        uses_secret = True

                if uses_secret:
                    ls_using_secret[ls.name] = ls

            if not ls_using_secret:
                return GetSecretUsageOutput(
                    secret_name=input_data.secret_name,
                    usage_count=0,
                    usages=[]
                )

            # Get all pipelines
            pipelines = self.adf_tools.get_all_pipelines()

            # Find pipelines using these linked services
            for pipeline in pipelines:
                for ls_name in pipeline.get('linked_services', []):
                    if ls_name in ls_using_secret:
                        # Determine if production critical
                        is_prod_critical = (
                            'prod' in pipeline['name'].lower() or
                            pipeline.get('environment') == 'prod'
                        )

                        usages.append(SecretUsage(
                            pipeline_name=pipeline['name'],
                            linked_service_name=ls_name,
                            environment=pipeline.get('environment', 'dev'),
                            is_production_critical=is_prod_critical
                        ))

            return GetSecretUsageOutput(
                secret_name=input_data.secret_name,
                usage_count=len(usages),
                usages=usages
            )

        except Exception as e:
            logger.error(f"Error analyzing secret usage: {str(e)}")
            raise
