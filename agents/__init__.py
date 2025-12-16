"""
Agent 集成模块
包含 Claude Code Sub Agent 客户端和 Function Call 定义
"""

from .claude_code_client import claude_code_client, execute_function_call
from .function_definitions import get_function_definitions

__all__ = ['claude_code_client', 'execute_function_call', 'get_function_definitions']

