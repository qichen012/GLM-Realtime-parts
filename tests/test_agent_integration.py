"""
测试 Claude Code Agent 集成
在运行完整系统前，先用这个脚本测试各个组件
"""

import json
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.claude_code_client import claude_code_client, execute_function_call


def test_connection():
    """测试基础连接"""
    print("\n" + "="*60)
    print("1. 测试 Claude Code 服务连接")
    print("="*60)
    
    print(f"📍 服务地址: {claude_code_client.base_url}")
    print(f"🔑 API Key: {'已配置' if claude_code_client.api_key else '未配置'}")
    
    # 可以添加一个 ping 接口测试
    # response = requests.get(f"{claude_code_client.base_url}/health")
    print("⚠️  请确保 Claude Code 服务正在运行")


def test_plan_trip():
    """测试行程规划"""
    print("\n" + "="*60)
    print("2. 测试行程规划 Agent")
    print("="*60)
    
    print("📋 测试参数:")
    params = {
        "destination": "北京",
        "start_date": "2024-02-01",
        "end_date": "2024-02-03",
        "preferences": "历史文化",
        "budget": "中等"
    }
    print(json.dumps(params, ensure_ascii=False, indent=2))
    
    print("\n🚀 开始调用...")
    try:
        result = claude_code_client.plan_trip(**params)
        print("\n✅ 调用成功！")
        print("📊 返回结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"\n❌ 调用失败: {e}")
        import traceback
        traceback.print_exc()


def test_book_ticket():
    """测试订票"""
    print("\n" + "="*60)
    print("3. 测试订票 Agent + Skill")
    print("="*60)
    
    print("🎫 测试参数:")
    params = {
        "ticket_type": "train",
        "departure_city": "北京",
        "arrival_city": "上海",
        "departure_date": "2024-02-01",
        "passenger_count": 1,
        "seat_class": "二等座"
    }
    print(json.dumps(params, ensure_ascii=False, indent=2))
    
    print("\n🚀 开始调用...")
    try:
        result = claude_code_client.book_ticket(**params)
        print("\n✅ 调用成功！")
        print("📊 返回结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"\n❌ 调用失败: {e}")
        import traceback
        traceback.print_exc()


def test_book_hotel():
    """测试订酒店"""
    print("\n" + "="*60)
    print("4. 测试订酒店 Agent + Skill")
    print("="*60)
    
    print("🏨 测试参数:")
    params = {
        "city": "杭州",
        "check_in_date": "2024-02-05",
        "check_out_date": "2024-02-08",
        "room_count": 1,
        "guest_count": 2,
        "hotel_type": "四星",
        "preferences": "靠近西湖"
    }
    print(json.dumps(params, ensure_ascii=False, indent=2))
    
    print("\n🚀 开始调用...")
    try:
        result = claude_code_client.book_hotel(**params)
        print("\n✅ 调用成功！")
        print("📊 返回结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"\n❌ 调用失败: {e}")
        import traceback
        traceback.print_exc()


def test_function_call_handler():
    """测试 function call 处理器"""
    print("\n" + "="*60)
    print("5. 测试 Function Call Handler")
    print("="*60)
    
    test_cases = [
        {
            "function_name": "plan_trip",
            "arguments": {
                "destination": "北京",
                "start_date": "2024-02-01",
                "end_date": "2024-02-03"
            }
        },
        {
            "function_name": "book_ticket",
            "arguments": {
                "ticket_type": "flight",
                "departure_city": "北京",
                "arrival_city": "上海",
                "departure_date": "2024-02-01",
                "passenger_count": 1
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"Function: {test_case['function_name']}")
        print(f"Arguments: {json.dumps(test_case['arguments'], ensure_ascii=False)}")
        
        try:
            result = execute_function_call(
                test_case['function_name'],
                test_case['arguments']
            )
            print(f"✅ 结果: {result.get('success', False)}")
            if result.get('error'):
                print(f"   错误: {result['error']}")
        except Exception as e:
            print(f"❌ 异常: {e}")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🧪"*30)
    print(" "*20 + "Claude Code Agent 集成测试")
    print("🧪"*30)
    
    test_connection()
    
    input("\n按 Enter 继续测试行程规划...")
    test_plan_trip()
    
    input("\n按 Enter 继续测试订票...")
    test_book_ticket()
    
    input("\n按 Enter 继续测试订酒店...")
    test_book_hotel()
    
    input("\n按 Enter 继续测试 Function Call Handler...")
    test_function_call_handler()
    
    print("\n" + "="*60)
    print("✅ 所有测试完成！")
    print("="*60)
    print("\n下一步:")
    print("1. 如果所有测试都通过，运行：python realtime_with_agent.py")
    print("2. 如果有测试失败，请检查:")
    print("   - Claude Code 服务是否运行")
    print("   - claude_code_config.py 配置是否正确")
    print("   - claude_code_client.py 接口格式是否匹配")


if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\n👋 测试中断")
    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()

