from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import sys
import os

# Ensure logs directory exists
os.makedirs("/app/logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import settings after logging is configured
from mcp_server.config import get_settings

settings = get_settings()

# Add file handler after settings are loaded
try:
    file_handler = logging.FileHandler(settings.log_file_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
except Exception as e:
    logger.warning(f"Could not create log file: {e}")

app = FastAPI(
    title="MCP DataOps Server",
    version="1.0.0",
    description="MCP server for DataOps tools"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy initialization of tool registry to avoid startup failures
_tool_registry = None


def get_tool_registry():
    global _tool_registry
    if _tool_registry is None:
        from mcp_server.tool_registry import ToolRegistry
        _tool_registry = ToolRegistry()
    return _tool_registry


class ToolExecutionRequest(BaseModel):
    tool_name: str
    input_data: Dict[str, Any]


class ToolExecutionResponse(BaseModel):
    tool_name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None


@app.get("/")
def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "MCP DataOps Server"}


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/tools")
def list_tools():
    """List all available MCP tools"""
    try:
        tool_registry = get_tool_registry()
        return {
            "tools": tool_registry.list_tools(),
            "count": len(tool_registry.tools)
        }
    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/{tool_name}")
def get_tool(tool_name: str):
    """Get specific tool schema"""
    try:
        tool_registry = get_tool_registry()
        tool = tool_registry.get_tool(tool_name)
        return {
            "name": tool['name'],
            "description": tool['description'],
            "input_schema": tool['input_schema'],
            "output_schema": tool['output_schema']
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/execute", response_model=ToolExecutionResponse)
def execute_tool(request: ToolExecutionRequest):
    """Execute an MCP tool"""
    try:
        logger.info(f"Executing tool: {request.tool_name}")
        
        tool_registry = get_tool_registry()
        result = tool_registry.execute_tool(
            name=request.tool_name,
            input_data=request.input_data
        )

        # Convert Pydantic model to dict if needed
        if hasattr(result, 'model_dump'):
            result = result.model_dump()
        elif hasattr(result, 'dict'):
            result = result.dict()

        return ToolExecutionResponse(
            tool_name=request.tool_name,
            success=True,
            result=result
        )

    except Exception as e:
        logger.error(f"Tool execution failed: {str(e)}", exc_info=True)
        return ToolExecutionResponse(
            tool_name=request.tool_name,
            success=False,
            error=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
