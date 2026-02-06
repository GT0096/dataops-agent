from typing import Dict, Any, Callable, List
from mcp_server.models.tool_schemas import *
from mcp_server.tools.adf_tools import ADFTools
from mcp_server.tools.keyvault_tools import KeyVaultTools
from mcp_server.tools.log_tools import LogTools
from mcp_server.tools.terraform_tools import TerraformTools
from mcp_server.tools.cloud_tools import CloudTools
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all MCP tools"""

    def __init__(self):
        # Initialize tool implementations
        self.adf_tools = ADFTools()
        self.kv_tools = KeyVaultTools()
        self.log_tools = LogTools()
        self.tf_tools = TerraformTools()
        self.cloud_tools = CloudTools()

        # Register all tools
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._register_all_tools()

    def _register_all_tools(self):
        """Register all available tools with their schemas"""

        # ADF Pipeline Tools
        self.register_tool(
            name="get_pipeline_status",
            description="Get current status and recent run history of an ADF pipeline",
            input_schema=GetPipelineStatusInput.model_json_schema(),
            output_schema=GetPipelineStatusOutput.model_json_schema(),
            handler=self.adf_tools.get_pipeline_status
        )

        self.register_tool(
            name="get_pipeline_dependencies",
            description="Analyze pipeline dependencies including upstream/downstream pipelines, datasets, and linked services",
            input_schema=GetPipelineDependenciesInput.model_json_schema(),
            output_schema=GetPipelineDependenciesOutput.model_json_schema(),
            handler=self.adf_tools.get_pipeline_dependencies
        )

        self.register_tool(
            name="get_failed_tasks_summary",
            description="Summarize failed activities across pipeline runs within a time window",
            input_schema=GetFailedTasksSummaryInput.model_json_schema(),
            output_schema=GetFailedTasksSummaryOutput.model_json_schema(),
            handler=self.adf_tools.get_failed_tasks_summary
        )

        # Key Vault Tools
        self.register_tool(
            name="get_keyvault_secrets",
            description="List secrets from Key Vault with metadata and risk levels",
            input_schema=GetKeyVaultSecretsInput.model_json_schema(),
            output_schema=GetKeyVaultSecretsOutput.model_json_schema(),
            handler=self.kv_tools.get_keyvault_secrets
        )

        self.register_tool(
            name="get_secret_usage",
            description="Find which pipelines and linked services use a specific secret",
            input_schema=GetSecretUsageInput.model_json_schema(),
            output_schema=GetSecretUsageOutput.model_json_schema(),
            handler=self.kv_tools.get_secret_usage
        )

        # Log Tools
        self.register_tool(
            name="fetch_logs",
            description="Fetch logs from ADF or application sources with filtering",
            input_schema=FetchLogsInput.model_json_schema(),
            output_schema=FetchLogsOutput.model_json_schema(),
            handler=self.log_tools.fetch_logs
        )

        self.register_tool(
            name="summarize_error_logs",
            description="Cluster and summarize error logs to identify patterns and anomalies",
            input_schema=SummarizeErrorLogsInput.model_json_schema(),
            output_schema=SummarizeErrorLogsOutput.model_json_schema(),
            handler=self.log_tools.summarize_error_logs
        )

        # Terraform Tools
        self.register_tool(
            name="parse_terraform_plan",
            description="Parse Terraform plan JSON and categorize resource changes with risk analysis",
            input_schema=ParseTerraformPlanInput.model_json_schema(),
            output_schema=ParseTerraformPlanOutput.model_json_schema(),
            handler=self.tf_tools.parse_terraform_plan
        )

        self.register_tool(
            name="detect_infra_drift",
            description="Detect drift between Terraform plan and actual Azure resources",
            input_schema=DetectInfraDriftInput.model_json_schema(),
            output_schema=DetectInfraDriftOutput.model_json_schema(),
            handler=self.tf_tools.detect_infra_drift
        )

        # Cloud Resource Tools
        self.register_tool(
            name="list_resources_by_tag",
            description="List Azure resources filtered by tag key and value",
            input_schema=ListResourcesByTagInput.model_json_schema(),
            output_schema=ListResourcesByTagOutput.model_json_schema(),
            handler=self.cloud_tools.list_resources_by_tag
        )

        logger.info(f"Registered {len(self.tools)} MCP tools")

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict,
        output_schema: Dict,
        handler: Callable
    ):
        """Register a single tool"""
        self.tools[name] = {
            'name': name,
            'description': description,
            'input_schema': input_schema,
            'output_schema': output_schema,
            'handler': handler
        }

    def get_tool(self, name: str) -> Dict[str, Any]:
        """Get tool definition by name"""
        if name not in self.tools:
            raise ValueError(f"Tool not found: {name}")
        return self.tools[name]

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools"""
        return [
            {
                'name': tool['name'],
                'description': tool['description'],
                'input_schema': tool['input_schema'],
                'output_schema': tool['output_schema']
            }
            for tool in self.tools.values()
        ]

    def execute_tool(self, name: str, input_data: Dict[str, Any]) -> Any:
        """Execute a tool by name with input data"""
        tool = self.get_tool(name)
        handler = tool['handler']

        # Parse input based on tool's input schema
        # In production, validate against schema
        logger.info(f"Executing tool: {name}")

        try:
            # Call handler (handlers expect Pydantic models)
            # Convert dict to appropriate Pydantic model
            input_model_class = self._get_input_model_class(name)
            if input_model_class:
                parsed_input = input_model_class(**input_data)
                result = handler(parsed_input)
            else:
                result = handler(**input_data)

            return result

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            raise

    def _get_input_model_class(self, tool_name: str):
        """Map tool name to input model class"""
        mapping = {
            'get_pipeline_status': GetPipelineStatusInput,
            'get_pipeline_dependencies': GetPipelineDependenciesInput,
            'get_failed_tasks_summary': GetFailedTasksSummaryInput,
            'get_keyvault_secrets': GetKeyVaultSecretsInput,
            'get_secret_usage': GetSecretUsageInput,
            'fetch_logs': FetchLogsInput,
            'summarize_error_logs': SummarizeErrorLogsInput,
            'parse_terraform_plan': ParseTerraformPlanInput,
            'detect_infra_drift': DetectInfraDriftInput,
            'list_resources_by_tag': ListResourcesByTagInput
        }
        return mapping.get(tool_name)
