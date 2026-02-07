# =============================================================================
# Terraform Outputs - MCP DataOps Assistant
# =============================================================================

# -----------------------------------------------------------------------------
# Resource Group
# -----------------------------------------------------------------------------
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_id" {
  description = "ID of the resource group"
  value       = azurerm_resource_group.main.id
}

# -----------------------------------------------------------------------------
# Storage Account
# -----------------------------------------------------------------------------
output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "storage_account_primary_key" {
  description = "Primary access key for the storage account"
  value       = azurerm_storage_account.main.primary_access_key
  sensitive   = true
}

# -----------------------------------------------------------------------------
# Key Vault
# -----------------------------------------------------------------------------
output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = azurerm_key_vault.main.vault_uri
}

# -----------------------------------------------------------------------------
# Data Factory
# -----------------------------------------------------------------------------
output "data_factory_name" {
  description = "Name of the Data Factory"
  value       = azurerm_data_factory.main.name
}

output "data_factory_id" {
  description = "ID of the Data Factory"
  value       = azurerm_data_factory.main.id
}

# -----------------------------------------------------------------------------
# Service Principal (for MCP Application)
# -----------------------------------------------------------------------------
output "mcp_client_id" {
  description = "Client ID (App ID) for the MCP service principal"
  value       = azuread_application.mcp_app.client_id
}

output "mcp_client_secret" {
  description = "Client secret for the MCP service principal"
  value       = azuread_application_password.mcp_sp_password.value
  sensitive   = true
}

output "tenant_id" {
  description = "Azure AD Tenant ID"
  value       = data.azurerm_client_config.current.tenant_id
}

output "subscription_id" {
  description = "Azure Subscription ID"
  value       = data.azurerm_client_config.current.subscription_id
}

# -----------------------------------------------------------------------------
# Environment Variables (for .env files)
# -----------------------------------------------------------------------------
output "env_file_mcp_server" {
  description = "Environment variables for mcp_server/.env"
  sensitive   = true
  value       = <<-EOT
    # Azure Authentication
    AZURE_TENANT_ID=${data.azurerm_client_config.current.tenant_id}
    AZURE_CLIENT_ID=${azuread_application.mcp_app.client_id}
    AZURE_CLIENT_SECRET=${azuread_application_password.mcp_sp_password.value}
    AZURE_SUBSCRIPTION_ID=${data.azurerm_client_config.current.subscription_id}

    # Azure Resources
    AZURE_RESOURCE_GROUP=${azurerm_resource_group.main.name}
    AZURE_DATA_FACTORY_NAME=${azurerm_data_factory.main.name}
    AZURE_KEY_VAULT_NAME=${azurerm_key_vault.main.name}
    AZURE_STORAGE_ACCOUNT_NAME=${azurerm_storage_account.main.name}

    # Application
    LOG_LEVEL=INFO
  EOT
}

output "env_file_backend" {
  description = "Environment variables for backend/.env (without OpenAI - add manually)"
  sensitive   = true
  value       = <<-EOT
    # Azure Authentication
    AZURE_TENANT_ID=${data.azurerm_client_config.current.tenant_id}
    AZURE_CLIENT_ID=${azuread_application.mcp_app.client_id}
    AZURE_CLIENT_SECRET=${azuread_application_password.mcp_sp_password.value}
    AZURE_SUBSCRIPTION_ID=${data.azurerm_client_config.current.subscription_id}

    # Azure OpenAI (ADD THESE MANUALLY)
    AZURE_OPENAI_ENDPOINT=https://YOUR-OPENAI.openai.azure.com/
    AZURE_OPENAI_API_KEY=YOUR-API-KEY
    AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
    AZURE_OPENAI_API_VERSION=2024-02-15-preview

    # MCP Server
    MCP_SERVER_URL=http://mcp-server:8001

    # Application
    ENVIRONMENT=dev
    LOG_LEVEL=INFO
  EOT
}
