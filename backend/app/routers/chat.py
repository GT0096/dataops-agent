from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from backend.app.llm_client import LLMClient
from backend.app.mcp_client import MCPClient
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize clients
llm_client = LLMClient()
mcp_client = MCPClient()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    environment: str = "dev"
    history: List[ChatMessage] = []


class ToolTrace(BaseModel):
    tool_name: str
    input_data: Dict[str, Any]
    output_data: Any


class ChatResponse(BaseModel):
    message: str
    tool_traces: List[ToolTrace] = []


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint that orchestrates LLM and MCP server.

    Flow:
    1. Build system prompt with context
    2. Send user message to LLM with available tools
    3. If LLM requests tool calls, execute via MCP server
    4. Feed tool results back to LLM
    5. Repeat until final answer
    6. Return answer with tool execution trace
    """
    try:
        logger.info(f"Chat request: {request.message[:100]}...")

        # Get available tools
        tools = mcp_client.get_tools_for_llm()

        # Build conversation messages
        messages = [
            {
                "role": "system",
                "content": llm_client.build_system_prompt(request.environment)
            }
        ]

        # Add history
        for msg in request.history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Add current user message
        messages.append({
            "role": "user",
            "content": request.message
        })

        # Track tool executions
        tool_traces = []

        # Conversation loop (max 10 iterations)
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Conversation iteration {iteration}")

            # Get LLM response
            llm_response = llm_client.chat(
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            # Check if LLM wants to call tools
            if llm_response.get("tool_calls"):
                logger.info(f"LLM requested {len(llm_response['tool_calls'])} tool calls")

                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": llm_response.get("content") or "",
                    "tool_calls": llm_response["tool_calls"]
                })

                # Execute each tool call
                for tool_call in llm_response["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_input = tool_call["function"]["arguments"]

                    try:
                        # Execute tool via MCP
                        tool_result = mcp_client.execute_tool(tool_name, tool_input)

                        # Track execution
                        tool_traces.append(ToolTrace(
                            tool_name=tool_name,
                            input_data=tool_input,
                            output_data=tool_result
                        ))

                        # Add tool result to conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": tool_name,
                            "content": str(tool_result)
                        })

                    except Exception as e:
                        logger.error(f"Tool execution error: {str(e)}")
                        # Add error as tool result
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": tool_name,
                            "content": f"Error executing tool: {str(e)}"
                        })
            else:
                # No more tool calls, we have final answer
                final_message = llm_response.get("content") or "No response generated"
                return ChatResponse(
                    message=final_message,
                    tool_traces=tool_traces
                )

        # Max iterations reached
        return ChatResponse(
            message="I apologize, but I couldn't complete the analysis within the allowed iterations.",
            tool_traces=tool_traces
        )

    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")
