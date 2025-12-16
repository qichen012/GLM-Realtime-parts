"""
Claude Code Sub Agent 客户端
用于调用 Claude Code 的 sub agent 和 skills
集成 Memobase 用户记忆功能
"""

import json
import requests
import sys
import os
from typing import Dict, Any, Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.memory_manager import format_memory_for_claude, DEFAULT_USER_ID


class ClaudeCodeClient:
    """Claude Code 客户端，用于调用 sub agent"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None, 
                 user_id: str = DEFAULT_USER_ID, enable_memory: bool = True):
        """
        初始化 Claude Code 客户端
        
        Args:
            base_url: Claude Code 服务的基础URL
            api_key: API 密钥（如果需要）
            user_id: 用户 ID（用于获取记忆）
            enable_memory: 是否启用记忆功能
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.user_id = user_id
        self.enable_memory = enable_memory
        self.headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    def _call_agent(self, agent_name: str, task: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 Claude Code Sub Agent（增强版：包含用户记忆）
        
        Args:
            agent_name: Agent 名称
            task: 任务描述
            parameters: 参数字典
            
        Returns:
            Agent 执行结果
        """
        try:
            # 🧠 如果启用记忆功能，将用户记忆加入任务描述
            enhanced_task = task
            if self.enable_memory:
                try:
                    memory_context = format_memory_for_claude(self.user_id)
                    if memory_context:
                        enhanced_task = f"""{task}

{memory_context}

请根据以上用户记忆提供个性化服务。"""
                        print("   🧠 已将用户记忆加入到 Agent 调用中")
                except Exception as mem_error:
                    print(f"   ⚠️ 获取用户记忆失败，使用原始任务: {mem_error}")
            
            # 方案 1: 如果你的同伴提供了统一的 agent 调用接口
            url = f"{self.base_url}/api/agent/execute"
            payload = {
                "agent_name": agent_name,
                "task": enhanced_task,  # 使用增强后的任务（包含记忆）
                "parameters": parameters
            }
            
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"调用 {agent_name} 失败"
            }
    
    def plan_trip(self, destination: str, start_date: str, end_date: str, 
                  preferences: Optional[str] = None, budget: Optional[str] = None) -> Dict[str, Any]:
        """
        调用行程规划 Agent
        
        Args:
            destination: 目的地
            start_date: 开始日期
            end_date: 结束日期
            preferences: 旅行偏好
            budget: 预算
            
        Returns:
            行程规划结果
        """
        parameters = {
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "preferences": preferences,
            "budget": budget
        }
        
        task = f"为我规划一次从{start_date}到{end_date}去{destination}的旅行"
        if preferences:
            task += f"，我的偏好是{preferences}"
        if budget:
            task += f"，预算是{budget}"
        
        print(f"📋 调用行程规划 Agent: {task}")
        result = self._call_agent("trip_planner", task, parameters)
        
        # 格式化返回结果
        if result.get("success"):
            return {
                "success": True,
                "itinerary": result.get("itinerary", []),
                "summary": result.get("summary", ""),
                "message": "行程规划完成"
            }
        else:
            return result
    
    def book_ticket(self, ticket_type: str, departure_city: str, arrival_city: str,
                   departure_date: str, passenger_count: int, return_date: Optional[str] = None,
                   seat_class: Optional[str] = None) -> Dict[str, Any]:
        """
        调用订票 Agent + 订票 Skill
        
        Args:
            ticket_type: 票务类型（flight/train/bus）
            departure_city: 出发城市
            arrival_city: 到达城市
            departure_date: 出发日期
            passenger_count: 乘客数量
            return_date: 返程日期（可选）
            seat_class: 座位等级（可选）
            
        Returns:
            订票结果
        """
        parameters = {
            "ticket_type": ticket_type,
            "departure_city": departure_city,
            "arrival_city": arrival_city,
            "departure_date": departure_date,
            "passenger_count": passenger_count,
            "return_date": return_date,
            "seat_class": seat_class
        }
        
        ticket_type_cn = {
            "flight": "飞机票",
            "train": "火车票",
            "bus": "汽车票"
        }.get(ticket_type, "票")
        
        task = f"帮我预订{departure_date}从{departure_city}到{arrival_city}的{ticket_type_cn}，{passenger_count}人"
        if return_date:
            task += f"，返程日期{return_date}"
        if seat_class:
            task += f"，座位等级{seat_class}"
        
        print(f"🎫 调用订票 Agent + Skill: {task}")
        result = self._call_agent("ticket_booking", task, parameters)
        
        if result.get("success"):
            return {
                "success": True,
                "tickets": result.get("tickets", []),
                "total_price": result.get("total_price", 0),
                "booking_reference": result.get("booking_reference", ""),
                "message": "订票成功"
            }
        else:
            return result
    
    def book_hotel(self, city: str, check_in_date: str, check_out_date: str,
                  room_count: int, guest_count: int, hotel_type: Optional[str] = None,
                  preferences: Optional[str] = None) -> Dict[str, Any]:
        """
        调用订酒店 Agent + 订酒店 Skill
        
        Args:
            city: 城市
            check_in_date: 入住日期
            check_out_date: 退房日期
            room_count: 房间数量
            guest_count: 入住人数
            hotel_type: 酒店类型
            preferences: 特殊需求
            
        Returns:
            订酒店结果
        """
        parameters = {
            "city": city,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "room_count": room_count,
            "guest_count": guest_count,
            "hotel_type": hotel_type,
            "preferences": preferences
        }
        
        task = f"帮我预订{city}的酒店，入住时间{check_in_date}到{check_out_date}，{room_count}间房，{guest_count}人"
        if hotel_type:
            task += f"，{hotel_type}酒店"
        if preferences:
            task += f"，要求：{preferences}"
        
        print(f"🏨 调用订酒店 Agent + Skill: {task}")
        result = self._call_agent("hotel_booking", task, parameters)
        
        if result.get("success"):
            return {
                "success": True,
                "hotels": result.get("hotels", []),
                "total_price": result.get("total_price", 0),
                "booking_reference": result.get("booking_reference", ""),
                "message": "订酒店成功"
            }
        else:
            return result


# 创建全局客户端实例
# 🔧 根据实际情况修改 base_url 和 api_key
claude_code_client = ClaudeCodeClient(
    base_url="http://localhost:8000",  # 👈 修改为实际的 Claude Code 服务地址
    api_key=None,  # 👈 如果需要，添加 API Key
    user_id=DEFAULT_USER_ID,  # 👈 用户 ID（用于获取记忆）
    enable_memory=True  # 👈 启用记忆功能
)


# 辅助函数：根据 function call 名称调用相应的 agent
def execute_function_call(function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行 function call
    
    Args:
        function_name: 函数名称
        arguments: 函数参数
        
    Returns:
        执行结果
    """
    try:
        if function_name == "plan_trip":
            return claude_code_client.plan_trip(**arguments)
        
        elif function_name == "book_ticket":
            return claude_code_client.book_ticket(**arguments)
        
        elif function_name == "book_hotel":
            return claude_code_client.book_hotel(**arguments)
        
        else:
            return {
                "success": False,
                "error": f"未知的函数: {function_name}",
                "message": "不支持的操作"
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"执行 {function_name} 时出错"
        }

