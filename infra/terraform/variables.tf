variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "rg-mcp-demo"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
  default     = "mcpdataops"
}

variable "key_vault_name" {
  description = "Name of the Key Vault (must be globally unique)"
  type        = string
  default     = "kv-mcp-demo"
}

variable "data_factory_name" {
  description = "Name of the Data Factory"
  type        = string
  default     = "adf-mcp-demo"
}

variable "storage_account_name" {
  description = "Name of the Storage Account (must be globally unique, lowercase, no hyphens)"
  type        = string
  default     = "stmcpdemo"
}

variable "admin_object_id" {
  description = "Object ID of the admin user/group for Key Vault access"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "MCP-DataOps"
    Environment = "dev"
    ManagedBy   = "Terraform"
  }
}
