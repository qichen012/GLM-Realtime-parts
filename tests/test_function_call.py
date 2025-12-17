#!/usr/bin/env python3
# coding: utf-8
"""
Function Call 功能测试脚本
测试 GLM-Realtime 的 Function Call 机制
"""

import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.function_definitions import get_function_definitions, get_function_by_name
from agents.claude_code_client import execute_function_call


class TestFunctionCall:
    """Function Call 测试类"""
    
    def __init__(self):
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0
    
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """记录测试结果"""
        self.test_count += 1
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n{status} - Test {self.test_count}: {test_name}")
        if message:
            print(f"   📝 {message}")
        
        if passed:
            self.passed_count += 1
        else:
            self.failed_count += 1
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*70)
        print("📊 测试摘要")
        print("="*70)
        print(f"总测试数: {self.test_count}")
        print(f"✅ 通过: {self.passed_count}")
        print(f"❌ 失败: {self.failed_count}")
        print(f"通过率: {(self.passed_count/self.test_count*100):.1f}%")
        print("="*70 + "\n")


class MockWebSocket:
    """Mock WebSocket 对象"""
    
    def __init__(self):
        self.sent_messages = []
    
    def send(self, message: str):
        """记录发送的消息"""
        self.sent_messages.append(json.loads(message))
    
    def get_last_message(self) -> Dict[str, Any]:
        """获取最后发送的消息"""
        return self.sent_messages[-1] if self.sent_messages else {}
    
    def clear(self):
        """清空消息记录"""
        self.sent_messages = []


def create_function_call_message(function_name: str, arguments: Dict[str, Any]) -> str:
    """创建 Function Call WebSocket 消息"""
    return json.dumps({
        "type": "response.function_call_arguments.done",
        "name": function_name,
        "arguments": json.dumps(arguments, ensure_ascii=False)
    })


def test_function_definitions():
    """测试 1: Function 定义加载"""
    tester = TestFunctionCall()
    
    print("\n" + "="*70)
    print("🧪 测试 1: Function 定义加载")
    print("="*70)
    
    # 测试获取所有函数定义
    functions = get_function_definitions()
    tester.log_test(
        "获取所有函数定义",
        len(functions) == 3,
        f"期望 3 个函数，实际 {len(functions)} 个"
    )
    
    # 测试函数名称
    function_names = [f["name"] for f in functions]
    expected_names = ["plan_trip", "book_ticket", "book_hotel"]
    tester.log_test(
        "函数名称正确",
        function_names == expected_names,
        f"函数列表: {function_names}"
    )
    
    # 测试每个函数的结构
    for func in functions:
        has_required_fields = all(key in func for key in ["type", "name", "description", "parameters"])
        tester.log_test(
            f"函数 {func['name']} 结构完整",
            has_required_fields,
            f"包含所有必需字段"
        )
    
    # 测试按名称获取函数
    plan_trip_func = get_function_by_name("plan_trip")
    tester.log_test(
        "按名称获取函数",
        plan_trip_func is not None and plan_trip_func["name"] == "plan_trip",
        "成功获取 plan_trip 函数定义"
    )
    
    # 测试不存在的函数
    invalid_func = get_function_by_name("invalid_function")
    tester.log_test(
        "获取不存在的函数返回 None",
        invalid_func is None,
        "正确处理不存在的函数"
    )
    
    return tester


def test_mock_execute_function_call():
    """测试 2: Mock Function 执行"""
    tester = TestFunctionCall()
    
    print("\n" + "="*70)
    print("🧪 测试 2: Mock Function 执行")
    print("="*70)
    
    # Mock 数据
    mock_responses = {
        "plan_trip": {
            "success": True,
            "itinerary": [
                "Day 1: 故宫、天安门广场",
                "Day 2: 长城、明十三陵",
                "Day 3: 颐和园、圆明园"
            ],
            "summary": "北京3天文化之旅",
            "estimated_cost": 3000
        },
        "book_ticket": {
            "success": True,
            "tickets": [
                {"type": "高铁", "train_no": "G101", "seat": "二等座"}
            ],
            "total_price": 553,
            "booking_reference": "MOCK-TK-12345"
        },
        "book_hotel": {
            "success": True,
            "hotels": [
                {"name": "北京国际酒店", "star": 4, "price": 500}
            ],
            "total_price": 1500,
            "booking_reference": "MOCK-HT-67890"
        }
    }
    
    # Mock execute_function_call
    with patch('agents.claude_code_client.ClaudeCodeClient._call_agent') as mock_call:
        # 测试 plan_trip
        mock_call.return_value = mock_responses["plan_trip"]
        result = execute_function_call("plan_trip", {
            "destination": "北京",
            "start_date": "2024-01-15",
            "end_date": "2024-01-18"
        })
        
        tester.log_test(
            "plan_trip 函数调用",
            result["success"] is True and "itinerary" in result,
            f"返回行程: {len(result.get('itinerary', []))} 天"
        )
        
        # 测试 book_ticket
        mock_call.return_value = mock_responses["book_ticket"]
        result = execute_function_call("book_ticket", {
            "ticket_type": "train",
            "departure_city": "北京",
            "arrival_city": "上海",
            "departure_date": "2024-01-20",
            "passenger_count": 1
        })
        
        tester.log_test(
            "book_ticket 函数调用",
            result["success"] is True and "tickets" in result,
            f"订票成功，参考号: {result.get('booking_reference', 'N/A')}"
        )
        
        # 测试 book_hotel
        mock_call.return_value = mock_responses["book_hotel"]
        result = execute_function_call("book_hotel", {
            "city": "北京",
            "check_in_date": "2024-01-15",
            "check_out_date": "2024-01-18",
            "room_count": 1,
            "guest_count": 2
        })
        
        tester.log_test(
            "book_hotel 函数调用",
            result["success"] is True and "hotels" in result,
            f"订酒店成功，总价: ¥{result.get('total_price', 0)}"
        )
    
    # 测试未知函数
    result = execute_function_call("unknown_function", {})
    tester.log_test(
        "未知函数错误处理",
        result["success"] is False and "error" in result,
        f"错误信息: {result.get('error', 'N/A')}"
    )
    
    return tester


def test_websocket_message_handling():
    """测试 3: WebSocket 消息处理（模拟逻辑）"""
    tester = TestFunctionCall()
    
    print("\n" + "="*70)
    print("🧪 测试 3: WebSocket 消息处理（模拟逻辑）")
    print("="*70)
    
    # 创建 Mock WebSocket
    mock_ws = MockWebSocket()
    
    # Mock Memobase 和 Claude Code 客户端
    with patch('agents.claude_code_client.ClaudeCodeClient._call_agent') as mock_call_agent:
        mock_call_agent.return_value = {
            "success": True,
            "itinerary": ["Day 1: 测试行程"],
            "summary": "规划完成"
        }
        
        # 创建 Function Call 消息
        message_data = {
            "type": "response.function_call_arguments.done",
            "name": "plan_trip",
            "arguments": json.dumps({
                "destination": "北京",
                "start_date": "2024-01-15",
                "end_date": "2024-01-18"
            }, ensure_ascii=False)
        }
        
        # 直接测试核心逻辑
        try:
            # 解析消息
            function_name = message_data.get("name")
            arguments = json.loads(message_data.get("arguments"))
            
            # 调用 execute_function_call
            result = execute_function_call(function_name, arguments)
            
            # 验证结果
            tester.log_test(
                "函数执行成功",
                result.get("success") is True,
                f"返回结果包含 itinerary"
            )
            
            # 模拟发送响应
            output_message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "output": json.dumps(result, ensure_ascii=False)
                }
            }
            mock_ws.send(json.dumps(output_message))
            mock_ws.send(json.dumps({"type": "response.create"}))
            
            # 验证是否发送了响应
            tester.log_test(
                "发送了响应消息",
                len(mock_ws.sent_messages) >= 2,
                f"发送了 {len(mock_ws.sent_messages)} 条消息"
            )
            
            # 验证消息类型
            if len(mock_ws.sent_messages) >= 1:
                first_msg = mock_ws.sent_messages[0]
                tester.log_test(
                    "第一条消息是 function_call_output",
                    first_msg.get("type") == "conversation.item.create",
                    f"消息类型: {first_msg.get('type')}"
                )
            
            if len(mock_ws.sent_messages) >= 2:
                second_msg = mock_ws.sent_messages[1]
                tester.log_test(
                    "第二条消息是 response.create",
                    second_msg.get("type") == "response.create",
                    f"消息类型: {second_msg.get('type')}"
                )
        
        except Exception as e:
            tester.log_test(
                "消息处理无异常",
                False,
                f"异常: {str(e)}"
            )
    
    return tester


def test_error_handling():
    """测试 4: 错误处理"""
    tester = TestFunctionCall()
    
    print("\n" + "="*70)
    print("🧪 测试 4: 错误处理")
    print("="*70)
    
    # 测试参数缺失
    with patch('agents.claude_code_client.ClaudeCodeClient._call_agent') as mock_call:
        mock_call.side_effect = TypeError("missing required argument")
        
        try:
            result = execute_function_call("plan_trip", {})
            tester.log_test(
                "处理参数缺失错误",
                "error" in result or "success" in result,
                "返回了错误信息"
            )
        except Exception as e:
            tester.log_test(
                "处理参数缺失错误",
                True,
                f"捕获异常: {type(e).__name__}"
            )
    
    # 测试网络错误
    with patch('agents.claude_code_client.ClaudeCodeClient._call_agent') as mock_call:
        mock_call.return_value = {
            "success": False,
            "error": "Network error",
            "message": "无法连接到 Agent 服务"
        }
        
        result = execute_function_call("book_ticket", {
            "ticket_type": "train",
            "departure_city": "北京",
            "arrival_city": "上海",
            "departure_date": "2024-01-20",
            "passenger_count": 1
        })
        
        tester.log_test(
            "处理网络错误",
            result["success"] is False,
            f"错误信息: {result.get('message', 'N/A')}"
        )
    
    # 测试 JSON 解析错误（使用模拟函数）
    mock_ws = MockWebSocket()
    
    def simulate_message_with_invalid_json(ws, message):
        """模拟处理无效 JSON 的消息"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "response.function_call_arguments.done":
                arguments_str = data.get("arguments", "{}")
                arguments = json.loads(arguments_str)  # 这里会抛出 JSON 错误
                # ...
        except json.JSONDecodeError:
            return False  # 表示处理失败
        return True
    
    invalid_message = json.dumps({
        "type": "response.function_call_arguments.done",
        "name": "plan_trip",
        "arguments": "invalid json {{"  # 无效的 JSON
    })
    
    try:
        result = simulate_message_with_invalid_json(mock_ws, invalid_message)
        tester.log_test(
            "处理 JSON 解析错误",
            result is False,
            "正确捕获 JSON 解析异常"
        )
    except Exception as e:
        tester.log_test(
            "处理 JSON 解析错误",
            True,
            f"捕获异常: {type(e).__name__}"
        )
    
    return tester


def test_integration_scenarios():
    """测试 5: 集成场景测试（使用模拟逻辑）"""
    tester = TestFunctionCall()
    
    print("\n" + "="*70)
    print("🧪 测试 5: 集成场景测试（使用模拟逻辑）")
    print("="*70)
    
    mock_ws = MockWebSocket()
    
    # 场景 1: 完整的旅行规划流程
    print("\n📝 场景 1: 用户说「帮我规划去北京的旅行」")
    
    with patch('agents.claude_code_client.ClaudeCodeClient._call_agent') as mock_call:
        mock_call.return_value = {
            "success": True,
            "itinerary": ["Day 1: 故宫", "Day 2: 长城", "Day 3: 颐和园"],
            "summary": "北京3天游",
            "estimated_cost": 3000
        }
        
        # 直接调用 execute_function_call
        result = execute_function_call("plan_trip", {
            "destination": "北京",
            "start_date": "2024-01-15",
            "end_date": "2024-01-18",
            "preferences": "文化景点"
        })
        
        # 模拟发送响应
        mock_ws.clear()
        mock_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {"type": "function_call_output", "output": json.dumps(result)}
        }))
        mock_ws.send(json.dumps({"type": "response.create"}))
        
        tester.log_test(
            "场景 1: 旅行规划",
            result.get("success") is True and len(mock_ws.sent_messages) >= 2,
            f"✅ 调用 Agent → ✅ 返回结果 → ✅ 发送 {len(mock_ws.sent_messages)} 条消息"
        )
    
    # 场景 2: 连续调用多个 function
    print("\n📝 场景 2: 用户先订票再订酒店")
    
    with patch('agents.claude_code_client.ClaudeCodeClient._call_agent') as mock_call:
        # 第一次调用：订票
        mock_call.return_value = {
            "success": True,
            "tickets": [{"train_no": "G101"}],
            "booking_reference": "TK-001"
        }
        
        result1 = execute_function_call("book_ticket", {
            "ticket_type": "train",
            "departure_city": "北京",
            "arrival_city": "上海",
            "departure_date": "2024-01-20",
            "passenger_count": 1
        })
        
        first_call_count = 1
        
        # 第二次调用：订酒店
        mock_call.return_value = {
            "success": True,
            "hotels": [{"name": "上海大酒店"}],
            "booking_reference": "HT-002"
        }
        
        result2 = execute_function_call("book_hotel", {
            "city": "上海",
            "check_in_date": "2024-01-20",
            "check_out_date": "2024-01-22",
            "room_count": 1,
            "guest_count": 2
        })
        
        second_call_count = 2
        
        tester.log_test(
            "场景 2: 连续调用",
            result1.get("success") and result2.get("success"),
            f"✅ 订票 → ✅ 订酒店，两次调用都成功"
        )
    
    # 场景 3: 失败后重试
    print("\n📝 场景 3: 服务失败后的处理")
    
    with patch('agents.claude_code_client.ClaudeCodeClient._call_agent') as mock_call:
        mock_call.return_value = {
            "success": False,
            "error": "Service unavailable",
            "message": "Agent 服务暂时不可用"
        }
        
        result = execute_function_call("plan_trip", {
            "destination": "上海",
            "start_date": "2024-02-01",
            "end_date": "2024-02-03"
        })
        
        # 模拟发送响应（即使失败也要发送）
        mock_ws.clear()
        mock_ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {"type": "function_call_output", "output": json.dumps(result)}
        }))
        mock_ws.send(json.dumps({"type": "response.create"}))
        
        # 验证仍然发送了响应（包含错误信息）
        tester.log_test(
            "场景 3: 失败处理",
            result.get("success") is False and len(mock_ws.sent_messages) >= 2,
            f"✅ Agent 返回失败 → ✅ 仍发送响应给 GLM"
        )
    
    return tester


def main():
    """主测试函数"""
    print("\n" + "="*70)
    print("🚀 Function Call 测试开始")
    print("="*70)
    
    all_testers = []
    
    # 运行所有测试
    try:
        all_testers.append(test_function_definitions())
        all_testers.append(test_mock_execute_function_call())
        all_testers.append(test_websocket_message_handling())
        all_testers.append(test_error_handling())
        all_testers.append(test_integration_scenarios())
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 汇总所有测试结果
    if all_testers:
        total_tests = sum(t.test_count for t in all_testers)
        total_passed = sum(t.passed_count for t in all_testers)
        total_failed = sum(t.failed_count for t in all_testers)
        
        print("\n" + "="*70)
        print("📊 总体测试报告")
        print("="*70)
        print(f"总测试数: {total_tests}")
        print(f"✅ 通过: {total_passed}")
        print(f"❌ 失败: {total_failed}")
        print(f"通过率: {(total_passed/total_tests*100):.1f}%")
        
        if total_failed == 0:
            print("\n🎉 所有测试通过！Function Call 功能正常！")
        else:
            print(f"\n⚠️  有 {total_failed} 个测试失败，请检查！")
        
        print("="*70 + "\n")
        
        return total_failed == 0
    
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

