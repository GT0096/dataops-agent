# MCP DataOps Assistant

An AI-powered DataOps Assistant that uses Model Context Protocol (MCP) to understand, inspect, and reason over Azure Data Factory pipelines, Key Vault secrets, infrastructure code, and operational logs.

![Architecture](https://img.shields.io/badge/Architecture-FastAPI%20%2B%20React%20%2B%20MCP-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![Node](https://img.shields.io/badge/Node.js-18+-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Azure Setup](#azure-setup)
3. [Local Development Setup](#local-development-setup)
4. [Docker Deployment](#docker-deployment)
5. [Configuration Reference](#configuration-reference)
6. [Testing the Application](#testing-the-application)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

- [ ] **Azure Account** - [Sign up for free ($200 credit)](https://azure.microsoft.com/free)
- [ ] **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop)
- [ ] **Git** - [Download here](https://git-scm.com/downloads)
- [ ] **Python 3.11+** (for local development only)
- [ ] **Node.js 18+** (for local development only)

---

## Azure Setup

### Step 1: Create Resource Group

```bash
# Login to Azure CLI
az login

# Create resource group
az group create --name rg-mcp-demo --location eastus
```

### Step 2: Create Azure Key Vault

```bash
# Create Key Vault
az keyvault create \
  --resource-group rg-mcp-demo \
  --name kv-mcp-demo \
  --location eastus

# Add sample secrets
az keyvault secret set --vault-name kv-mcp-demo --name "db-connection-string-dev" --value "Server=dev-server;Database=mydb;User=admin;Password=secret123"
az keyvault secret set --vault-name kv-mcp-demo --name "db-connection-string-prod" --value "Server=prod-server;Database=mydb;User=admin;Password=prodsecret456"
az keyvault secret set --vault-name kv-mcp-demo --name "api-key-external" --value "ext-api-key-12345"
```

### Step 3: Create Azure Data Factory

```bash
# Create Data Factory
az datafactory create \
  --resource-group rg-mcp-demo \
  --name adf-mcp-demo \
  --location eastus
```

After creation, go to **Azure Portal → Data Factory → Author & Monitor** to create sample pipelines:

1. **Create Linked Services:**
   - `LinkedService_KeyVault` → Connect to your Key Vault
   - `LinkedService_AzureSQL` → Reference connection string from Key Vault

2. **Create Sample Pipelines:**
   - `ingest_customer_data` - A simple Copy activity
   - `transform_sales_data` - Execute Pipeline activity calling ingest_customer_data
   - `export_reports` - Another Copy activity

### Step 4: Create Azure OpenAI (or use OpenAI directly)

**Option A: Azure OpenAI** (requires approval, 1-5 days)
```bash
# Request access at: https://aka.ms/oai/access
# After approval:
az cognitiveservices account create \
  --name openai-mcp-demo \
  --resource-group rg-mcp-demo \
  --kind OpenAI \
  --sku S0 \
  --location eastus

# Deploy GPT-4 model via Azure Portal
```

**Option B: OpenAI directly** (faster, recommended for demo)
1. Go to https://platform.openai.com/signup
2. Create API key at https://platform.openai.com/api-keys
3. You get $5 free credit

### Step 5: Create Service Principal

```bash
# Create service principal with Contributor role
az ad sp create-for-rbac \
  --name "mcp-dataops-sp" \
  --role Contributor \
  --scopes /subscriptions/<YOUR_SUBSCRIPTION_ID>/resourceGroups/rg-mcp-demo

# Save the output! You'll need:
# - appId (this is AZURE_CLIENT_ID)
# - password (this is AZURE_CLIENT_SECRET)
# - tenant (this is AZURE_TENANT_ID)

# Grant Key Vault access to the service principal
az keyvault set-policy \
  --name kv-mcp-demo \
  --spn <APP_ID_FROM_ABOVE> \
  --secret-permissions get list

# Grant Data Factory access
az role assignment create \
  --assignee <APP_ID_FROM_ABOVE> \
  --role "Data Factory Contributor" \
  --scope /subscriptions/<YOUR_SUBSCRIPTION_ID>/resourceGroups/rg-mcp-demo
```

### Step 6: Get Your Subscription ID

```bash
az account show --query id -o tsv
```

---

## Local Development Setup

### Step 1: Clone Repository

```bash
git clone <your-repo-url>
cd dataops_pranjal
```

### Step 2: Configure Environment Files

```bash
# Copy example files
copy backend\.env.example backend\.env
copy mcp_server\.env.example mcp_server\.env
copy frontend\.env.example frontend\.env
```

### Step 3: Edit backend/.env

```env
# Azure Authentication (from Service Principal)
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<your-client-id>
AZURE_CLIENT_SECRET=<your-client-secret>
AZURE_SUBSCRIPTION_ID=<your-subscription-id>

# Azure OpenAI (if using Azure OpenAI)
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# MCP Server URL (for local development)
MCP_SERVER_URL=http://localhost:8001

# Application
ENVIRONMENT=dev
LOG_LEVEL=INFO
```

### Step 4: Edit mcp_server/.env

```env
# Azure Authentication (same as backend)
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<your-client-id>
AZURE_CLIENT_SECRET=<your-client-secret>
AZURE_SUBSCRIPTION_ID=<your-subscription-id>

# Azure Resources
AZURE_RESOURCE_GROUP=rg-mcp-demo
AZURE_DATA_FACTORY_NAME=adf-mcp-demo
AZURE_KEY_VAULT_NAME=kv-mcp-demo
AZURE_STORAGE_ACCOUNT_NAME=stmcpdemo

# Application
LOG_LEVEL=INFO
```

### Step 5: Start MCP Server

```bash
cd mcp_server
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
python main.py
```

Server runs at: http://localhost:8001

### Step 6: Start Backend (new terminal)

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate

pip install -r requirements.txt
python -m app.main
```

Server runs at: http://localhost:8000

### Step 7: Start Frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

App runs at: http://localhost:3000

---

## Docker Deployment

### Step 1: Configure Environment Files

```bash
copy backend\.env.example backend\.env
copy mcp_server\.env.example mcp_server\.env
```

Edit both `.env` files with your Azure credentials (see Step 3 & 4 above).

### Step 2: Build and Run

```bash
docker-compose up --build
```

### Step 3: Access Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **MCP Server**: http://localhost:8001

### Step 4: Stop Application

```bash
docker-compose down
```

---

## Configuration Reference

### Backend Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_TENANT_ID` | Azure AD tenant ID | ✅ |
| `AZURE_CLIENT_ID` | Service principal app ID | ✅ |
| `AZURE_CLIENT_SECRET` | Service principal secret | ✅ |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | ✅ |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | ✅ |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | ✅ |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Model deployment name | ✅ |
| `MCP_SERVER_URL` | MCP server URL | ✅ |
| `ENVIRONMENT` | Environment name (dev/prod) | ❌ |

### MCP Server Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_TENANT_ID` | Azure AD tenant ID | ✅ |
| `AZURE_CLIENT_ID` | Service principal app ID | ✅ |
| `AZURE_CLIENT_SECRET` | Service principal secret | ✅ |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | ✅ |
| `AZURE_RESOURCE_GROUP` | Resource group name | ✅ |
| `AZURE_DATA_FACTORY_NAME` | Data Factory name | ✅ |
| `AZURE_KEY_VAULT_NAME` | Key Vault name | ✅ |
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account name | ❌ |

---

## Testing the Application

### Example Queries to Try

Once the application is running, try these queries:

1. **Pipeline Status**
   ```
   What is the status of the ingest_customer_data pipeline?
   ```

2. **Secret Impact Analysis**
   ```
   If I rotate the db-connection-string-prod secret, what will break?
   ```

3. **Error Investigation**
   ```
   Why did the transform_sales_data pipeline fail yesterday?
   ```

4. **Dependency Analysis**
   ```
   What are the dependencies of the export_reports pipeline?
   ```

5. **Log Summarization**
   ```
   Summarize the errors from the last 24 hours
   ```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /` | GET | Health check |
| `GET /health` | GET | Health status |
| `POST /chat` | POST | Send chat message |
| `GET /tools` | GET | List MCP tools |
| `POST /execute` | POST | Execute MCP tool |

---

## Troubleshooting

### Common Issues

**1. "Azure credentials not found"**
```
Error: DefaultAzureCredential failed
```
**Solution:** Ensure all AZURE_* environment variables are set correctly in `.env` files.

**2. "Key Vault access denied"**
```
Error: Access denied to Key Vault
```
**Solution:** Grant the service principal access:
```bash
az keyvault set-policy --name kv-mcp-demo --spn <CLIENT_ID> --secret-permissions get list
```

**3. "Data Factory not found"**
```
Error: DataFactory 'adf-mcp-demo' not found
```
**Solution:** Verify `AZURE_DATA_FACTORY_NAME` matches your actual ADF name.

**4. "OpenAI rate limited"**
```
Error: Rate limit exceeded
```
**Solution:** Wait a minute or upgrade your OpenAI plan.

**5. Docker build fails**
```
Error: npm install failed
```
**Solution:** Ensure Docker has enough memory (4GB minimum).

### Logs Location

- **MCP Server logs**: `./logs/mcp_server.log`
- **Docker logs**: `docker-compose logs -f <service-name>`

### Cleanup Azure Resources

To avoid charges, delete all resources when done:

```bash
az group delete --name rg-mcp-demo --yes --no-wait
```

---

## Project Structure

```
mcp-dataops-assistant/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── config.py         # Settings
│   │   ├── llm_client.py     # Azure OpenAI client
│   │   ├── mcp_client.py     # MCP protocol client
│   │   ├── main.py           # FastAPI entry
│   │   └── routers/chat.py   # Chat endpoint
│   └── requirements.txt
│
├── mcp_server/               # MCP tool server
│   ├── config.py
│   ├── main.py
│   ├── tool_registry.py
│   ├── models/tool_schemas.py
│   ├── tools/
│   │   ├── adf_tools.py
│   │   ├── keyvault_tools.py
│   │   ├── log_tools.py
│   │   ├── terraform_tools.py
│   │   └── cloud_tools.py
│   └── utils/azure_client.py
│
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   └── services/api.js
│   └── package.json
│
├── infra/terraform/          # Infrastructure as Code
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.mcp
└── README.md
```

---

## License

MIT License - See LICENSE file for details.
