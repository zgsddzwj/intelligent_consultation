"""MCP请求处理器"""
from typing import Dict, Any, List
from app.knowledge.mcp.tools import MCPTools
from app.utils.logger import app_logger


class MCPHandlers:
    """MCP请求处理器"""
    
    def __init__(self):
        self.tools = MCPTools()
    
    def handle_list_tools(self) -> Dict[str, Any]:
        """处理列出工具请求"""
        return {
            "tools": self.tools.get_tools()
        }
    
    def handle_call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用请求"""
        try:
            result = self.tools.execute_tool(tool_name, parameters)
            return {
                "tool": tool_name,
                "result": result,
                "success": True
            }
        except Exception as e:
            app_logger.error(f"MCP工具调用失败: {tool_name}, {e}")
            return {
                "tool": tool_name,
                "error": str(e),
                "success": False
            }
    
    def handle_batch_call(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量调用工具"""
        results = []
        for call in tool_calls:
            tool_name = call.get("tool")
            parameters = call.get("parameters", {})
            result = self.handle_call_tool(tool_name, parameters)
            results.append(result)
        return results

