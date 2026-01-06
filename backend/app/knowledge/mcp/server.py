"""MCP服务器主程序"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.knowledge.mcp.handlers import MCPHandlers
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()
handlers = MCPHandlers()

# 创建MCP服务器应用
mcp_app = FastAPI(
    title="MCP Server",
    description="Model Context Protocol Server for Medical Consultation",
    version="0.1.0"
)


class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool: str
    parameters: Dict[str, Any]


class BatchToolCallRequest(BaseModel):
    """批量工具调用请求"""
    tools: List[ToolCallRequest]


@mcp_app.get("/")
async def root():
    """根路径"""
    return {
        "name": "MCP Server",
        "version": "0.1.0",
        "status": "running"
    }


@mcp_app.get("/tools")
async def list_tools():
    """列出所有可用工具"""
    try:
        return handlers.handle_list_tools()
    except Exception as e:
        app_logger.error(f"列出工具失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_app.post("/tools/call")
async def call_tool(request: ToolCallRequest):
    """调用单个工具"""
    try:
        return handlers.handle_call_tool(request.tool, request.parameters)
    except Exception as e:
        app_logger.error(f"工具调用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_app.post("/tools/batch")
async def batch_call_tools(request: BatchToolCallRequest):
    """批量调用工具"""
    try:
        tool_calls = [
            {"tool": tool.tool, "parameters": tool.parameters}
            for tool in request.tools
        ]
        results = handlers.handle_batch_call(tool_calls)
        return {"results": results}
    except Exception as e:
        app_logger.error(f"批量工具调用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@mcp_app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

