import httpx
from typing import Dict, Any, List
from backend.app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class MCPClient:
    """Client for communicating with MCP server"""

    def __init__(self):
        self.base_url = settings.mcp_server_url
        self.client = httpx.Client(timeout=30.0)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from MCP server"""
        try:
            response = self.client.get(f"{self.base_url}/tools")
            response.raise_for_status()
            data = response.json()
            return data.get("tools", [])
        except Exception as e:
            logger.error(f"Error listing MCP tools: {str(e)}")
            raise

    def execute_tool(self, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on MCP server"""
        try:
            logger.info(f"Executing MCP tool: {tool_name}")
            response = self.client.post(
                f"{self.base_url}/execute",
                json={
                    "tool_name": tool_name,
                    "input_data": input_data
                }
            )
            response.raise_for_status()
            result = response.json()

            if not result.get("success"):
                raise Exception(f"Tool execution failed: {result.get('error')}")

            return result.get("result")

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            raise

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI function format"""
        tools = self.list_tools()
        llm_tools = []

        for tool in tools:
            llm_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            })

        return llm_tools
