"""
Claude Code 配置文件
根据你的实际部署情况修改这些配置
"""

# Claude Code 服务配置
CLAUDE_CODE_CONFIG = {
    # 基础URL - 修改为实际的服务地址
    "base_url": "http://localhost:8000",
    
    # API Key（如果需要）
    "api_key": None,
    
    # Agent 名称映射（根据实际情况修改）
    "agents": {
        "trip_planner": {
            "name": "行程规划 Agent",
            "endpoint": "/api/agent/trip-planner"  # 可选：如果有专门的endpoint
        },
        "ticket_booking": {
            "name": "订票 Agent",
            "endpoint": "/api/agent/ticket-booking",
            "skill": "ticket_booking_skill"  # 关联的 skill
        },
        "hotel_booking": {
            "name": "订酒店 Agent", 
            "endpoint": "/api/agent/hotel-booking",
            "skill": "hotel_booking_skill"  # 关联的 skill
        }
    },
    
    # 超时配置
    "timeout": 30,
    
    # 重试配置
    "max_retries": 3,
    "retry_delay": 1
}


# 根据你同伴的实际接口格式，可能需要调整这些
# 方案 A: 统一的 agent 调用接口
AGENT_API_FORMAT_A = {
    "url_pattern": "{base_url}/api/agent/execute",
    "request_format": {
        "agent_name": "agent_name",
        "task": "task_description",
        "parameters": {}
    }
}

# 方案 B: 每个 agent 有独立的接口
AGENT_API_FORMAT_B = {
    "url_pattern": "{base_url}/api/{agent_name}/execute",
    "request_format": {
        "task": "task_description",
        "params": {}
    }
}

# 方案 C: MCP 协议
MCP_CONFIG = {
    "enabled": False,  # 如果使用 MCP，设置为 True
    "mcp_server_url": "http://localhost:3000",
    "tools": [
        "plan_trip",
        "book_ticket",
        "book_hotel"
    ]
}

