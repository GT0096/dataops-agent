from openai import AzureOpenAI
from typing import List, Dict, Any, Optional
from backend.app.config import get_settings
import json
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMClient:
    """Azure OpenAI client for chat completions with tool calling"""

    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint
        )
        self.deployment = settings.azure_openai_deployment_name

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto"
    ) -> Dict[str, Any]:
        """
        Send chat completion request with optional tool calling.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: List of available tool definitions
            tool_choice: "auto", "none", or specific tool

        Returns:
            Response dict with message and optional tool_calls
        """
        try:
            logger.info(f"Sending chat request with {len(messages)} messages")

            request_params = {
                "model": self.deployment,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }

            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = tool_choice

            response = self.client.chat.completions.create(**request_params)
            message = response.choices[0].message

            result = {
                "role": message.role,
                "content": message.content,
                "tool_calls": []
            }

            # Extract tool calls if present
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    result["tool_calls"].append({
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": json.loads(tool_call.function.arguments)
                        }
                    })

            return result

        except Exception as e:
            logger.error(f"LLM chat error: {str(e)}")
            raise

    def build_system_prompt(self, environment: str = "dev") -> str:
        """Build system prompt for DataOps assistant"""
        return f"""You are an expert DataOps assistant with deep knowledge of Azure Data Factory, Key Vault, and infrastructure management.

Your role:
- Analyze pipeline failures and identify root causes
- Explain dependencies and impacts
- Correlate failures across pipelines, secrets, and infrastructure
- Provide evidence-based explanations using tool results

Current environment: {environment}

When answering:
1. Use available tools to gather facts
2. Correlate information across systems (ADF, Key Vault, logs, infrastructure)
3. Provide specific, actionable insights
4. Always cite evidence from tool results
5. Explain in clear, technical language

Available data sources:
- Azure Data Factory pipelines and runs
- Azure Key Vault secrets and usage
- Pipeline and application logs
- Terraform infrastructure plans
- Azure cloud resources

Be thorough, precise, and always ground your explanations in actual data."""
