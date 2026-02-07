# =============================================================================
# MCP DataOps Assistant - Azure Infrastructure
# =============================================================================

# -----------------------------------------------------------------------------
# Resource Group
# -----------------------------------------------------------------------------
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# -----------------------------------------------------------------------------
# Storage Account (for Data Factory staging and logs)
# -----------------------------------------------------------------------------
resource "azurerm_storage_account" "main" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = var.tags
}

# Create containers for data
resource "azurerm_storage_container" "raw" {
  name                  = "raw-data"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "processed" {
  name                  = "processed-data"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# -----------------------------------------------------------------------------
# Key Vault
# -----------------------------------------------------------------------------
resource "azurerm_key_vault" "main" {
  name                        = var.key_vault_name
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  enabled_for_disk_encryption = false
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false
  sku_name                    = "standard"

  tags = var.tags
}

# Access policy for Terraform deployer
resource "azurerm_key_vault_access_policy" "deployer" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get", "List", "Set", "Delete", "Purge", "Recover"
  ]
}

# Access policy for admin (if provided)
resource "azurerm_key_vault_access_policy" "admin" {
  count = var.admin_object_id != "" ? 1 : 0

  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = var.admin_object_id

  secret_permissions = [
    "Get", "List", "Set", "Delete", "Purge", "Recover"
  ]
}

# Sample secrets
resource "azurerm_key_vault_secret" "db_connection_dev" {
  name         = "db-connection-string-dev"
  value        = "Server=dev-server.database.windows.net;Database=devdb;User=admin;Password=DevPassword123!"
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.deployer]

  tags = {
    environment = "dev"
    risk        = "low"
  }
}

resource "azurerm_key_vault_secret" "db_connection_prod" {
  name         = "db-connection-string-prod"
  value        = "Server=prod-server.database.windows.net;Database=proddb;User=admin;Password=ProdPassword456!"
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.deployer]

  tags = {
    environment = "prod"
    risk        = "high"
  }
}

resource "azurerm_key_vault_secret" "api_key_external" {
  name         = "api-key-external-service"
  value        = "ext-api-key-abc123xyz789"
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.deployer]

  tags = {
    environment = "all"
    risk        = "medium"
  }
}

resource "azurerm_key_vault_secret" "storage_key" {
  name         = "storage-account-key"
  value        = azurerm_storage_account.main.primary_access_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.deployer]

  tags = {
    environment = "all"
    risk        = "high"
  }
}

# -----------------------------------------------------------------------------
# Data Factory
# -----------------------------------------------------------------------------
resource "azurerm_data_factory" "main" {
  name                = var.data_factory_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Grant Data Factory access to Key Vault
resource "azurerm_key_vault_access_policy" "data_factory" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_data_factory.main.identity[0].principal_id

  secret_permissions = [
    "Get", "List"
  ]
}

# -----------------------------------------------------------------------------
# Data Factory Linked Services
# -----------------------------------------------------------------------------

# Linked Service: Key Vault
resource "azurerm_data_factory_linked_service_key_vault" "main" {
  name            = "LinkedService_KeyVault"
  data_factory_id = azurerm_data_factory.main.id
  key_vault_id    = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.data_factory]
}

# Linked Service: Azure Blob Storage
resource "azurerm_data_factory_linked_service_azure_blob_storage" "main" {
  name              = "LinkedService_AzureBlob"
  data_factory_id   = azurerm_data_factory.main.id
  connection_string = azurerm_storage_account.main.primary_connection_string
}

# -----------------------------------------------------------------------------
# Data Factory Datasets
# -----------------------------------------------------------------------------

# Dataset: Raw Data (Blob)
resource "azurerm_data_factory_dataset_json" "raw_data" {
  name                = "Dataset_RawData"
  data_factory_id     = azurerm_data_factory.main.id
  linked_service_name = azurerm_data_factory_linked_service_azure_blob_storage.main.name

  azure_blob_storage_location {
    container = azurerm_storage_container.raw.name
    path      = "input"
    filename  = "*.json"
  }

  encoding = "UTF-8"
}

# Dataset: Processed Data (Blob)
resource "azurerm_data_factory_dataset_json" "processed_data" {
  name                = "Dataset_ProcessedData"
  data_factory_id     = azurerm_data_factory.main.id
  linked_service_name = azurerm_data_factory_linked_service_azure_blob_storage.main.name

  azure_blob_storage_location {
    container = azurerm_storage_container.processed.name
    path      = "output"
    filename  = "processed.json"
  }

  encoding = "UTF-8"
}

# -----------------------------------------------------------------------------
# Data Factory Pipelines
# -----------------------------------------------------------------------------

# Pipeline 1: Ingest Customer Data
resource "azurerm_data_factory_pipeline" "ingest_customer_data" {
  name            = "ingest_customer_data"
  data_factory_id = azurerm_data_factory.main.id
  description     = "Ingests customer data from raw storage"

  activities_json = jsonencode([
    {
      name = "WaitForData"
      type = "Wait"
      typeProperties = {
        waitTimeInSeconds = 5
      }
    }
  ])
}

# Pipeline 2: Transform Sales Data (depends on ingest)
resource "azurerm_data_factory_pipeline" "transform_sales_data" {
  name            = "transform_sales_data"
  data_factory_id = azurerm_data_factory.main.id
  description     = "Transforms sales data after customer data is ingested"

  activities_json = jsonencode([
    {
      name = "ExecuteIngestPipeline"
      type = "ExecutePipeline"
      typeProperties = {
        pipeline = {
          referenceName = azurerm_data_factory_pipeline.ingest_customer_data.name
          type          = "PipelineReference"
        }
        waitOnCompletion = true
      }
    },
    {
      name      = "TransformData"
      type      = "Wait"
      dependsOn = [
        {
          activity             = "ExecuteIngestPipeline"
          dependencyConditions = ["Succeeded"]
        }
      ]
      typeProperties = {
        waitTimeInSeconds = 3
      }
    }
  ])
}

# Pipeline 3: Export Reports (downstream of transform)
resource "azurerm_data_factory_pipeline" "export_reports" {
  name            = "export_reports"
  data_factory_id = azurerm_data_factory.main.id
  description     = "Exports processed data to reports container"

  activities_json = jsonencode([
    {
      name = "CopyToReports"
      type = "Copy"
      typeProperties = {
        source = {
          type = "JsonSource"
          storeSettings = {
            type      = "AzureBlobStorageReadSettings"
            recursive = false
          }
        }
        sink = {
          type = "JsonSink"
          storeSettings = {
            type = "AzureBlobStorageWriteSettings"
          }
        }
      }
      inputs = [
        {
          referenceName = azurerm_data_factory_dataset_json.raw_data.name
          type          = "DatasetReference"
        }
      ]
      outputs = [
        {
          referenceName = azurerm_data_factory_dataset_json.processed_data.name
          type          = "DatasetReference"
        }
      ]
    }
  ])
}

# -----------------------------------------------------------------------------
# Service Principal for MCP Application
# -----------------------------------------------------------------------------
resource "azuread_application" "mcp_app" {
  display_name = "mcp-dataops-assistant"
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "mcp_sp" {
  client_id                    = azuread_application.mcp_app.client_id
  app_role_assignment_required = false
  owners                       = [data.azuread_client_config.current.object_id]
}

resource "azuread_application_password" "mcp_sp_password" {
  application_id = azuread_application.mcp_app.id
  display_name   = "mcp-app-secret"
  end_date       = "2026-12-31T00:00:00Z"
}

# Grant Service Principal access to Key Vault
resource "azurerm_key_vault_access_policy" "mcp_sp" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azuread_service_principal.mcp_sp.object_id

  secret_permissions = [
    "Get", "List"
  ]
}

# Grant Service Principal Contributor role on Resource Group
resource "azurerm_role_assignment" "mcp_sp_contributor" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.mcp_sp.object_id
}

# Grant Service Principal Data Factory Contributor role
resource "azurerm_role_assignment" "mcp_sp_adf" {
  scope                = azurerm_data_factory.main.id
  role_definition_name = "Data Factory Contributor"
  principal_id         = azuread_service_principal.mcp_sp.object_id
}
