#!/usr/bin/env python3
# coding: utf-8
"""
测试记忆集成功能
测试 Memobase 记忆是否正确加载到 GLM 和 Claude Code 中
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.memory_manager import (
    get_user_memory, 
    format_memory_for_glm,
    format_memory_for_claude,
    memory_manager,
    DEFAULT_USER_ID
)

def test_memory_connection():
    """测试 Memobase 连接"""
    print("="*60)
    print("📡 测试 1: Memobase 连接")
    print("="*60)
    
    try:
        client = memory_manager.client
        if client:
            ok = client.ping()
            if ok:
                print("✅ Memobase 连接成功！")
                return True
            else:
                print("❌ Memobase healthcheck 失败")
                return False
        else:
            print("❌ 无法创建 Memobase 客户端")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_get_user_memory():
    """测试获取用户记忆"""
    print("\n" + "="*60)
    print("🧠 测试 2: 获取用户记忆")
    print("="*60)
    
    try:
        memory = get_user_memory(DEFAULT_USER_ID)
        if memory:
            print(f"✅ 成功获取用户记忆 ({len(memory)} 字符)")
            print("\n前 500 个字符预览:")
            print("-" * 60)
            print(memory[:500] + "..." if len(memory) > 500 else memory)
            print("-" * 60)
            return True
        else:
            print("⚠️ 未获取到记忆内容（可能是空的或连接失败）")
            return False
    except Exception as e:
        print(f"❌ 获取记忆失败: {e}")
        return False

def test_format_for_glm():
    """测试为 GLM 格式化记忆"""
    print("\n" + "="*60)
    print("🤖 测试 3: 为 GLM-Realtime 格式化记忆")
    print("="*60)
    
    try:
        formatted = format_memory_for_glm(DEFAULT_USER_ID)
        if formatted:
            print(f"✅ 成功格式化 ({len(formatted)} 字符)")
            print("\n格式化结果预览:")
            print("-" * 60)
            lines = formatted.split('\n')
            preview_lines = lines[:20] if len(lines) > 20 else lines
            print('\n'.join(preview_lines))
            if len(lines) > 20:
                print(f"... (还有 {len(lines) - 20} 行)")
            print("-" * 60)
            return True
        else:
            print("⚠️ 格式化结果为空")
            return False
    except Exception as e:
        print(f"❌ 格式化失败: {e}")
        return False

def test_format_for_claude():
    """测试为 Claude Code 格式化记忆"""
    print("\n" + "="*60)
    print("🧑‍💻 测试 4: 为 Claude Code 格式化记忆")
    print("="*60)
    
    try:
        formatted = format_memory_for_claude(DEFAULT_USER_ID)
        if formatted:
            print(f"✅ 成功格式化 ({len(formatted)} 字符)")
            return True
        else:
            print("⚠️ 格式化结果为空")
            return False
    except Exception as e:
        print(f"❌ 格式化失败: {e}")
        return False

def test_user_profile():
    """测试获取用户画像"""
    print("\n" + "="*60)
    print("👤 测试 5: 获取用户画像")
    print("="*60)
    
    try:
        summary = memory_manager.get_user_profile_summary(DEFAULT_USER_ID)
        if summary:
            print(f"✅ 成功获取用户画像")
            print("\n用户画像预览:")
            print("-" * 60)
            print(summary)
            print("-" * 60)
            return True
        else:
            print("⚠️ 未获取到用户画像")
            return False
    except Exception as e:
        print(f"❌ 获取画像失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("\n" + "🧪 " + "="*55)
    print("   Memobase 记忆集成测试")
    print("="*60 + "\n")
    
    results = []
    
    # 运行所有测试
    results.append(("Memobase 连接", test_memory_connection()))
    results.append(("获取用户记忆", test_get_user_memory()))
    results.append(("GLM 格式化", test_format_for_glm()))
    results.append(("Claude 格式化", test_format_for_claude()))
    results.append(("用户画像", test_user_profile()))
    
    # 输出总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！记忆集成功能正常！")
        print("\n💡 下一步:")
        print("   1. 确保 Memobase 服务运行在 http://localhost:8019/")
        print("   2. 运行 python realtime_with_agent.py 测试完整功能")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查:")
        print("   1. Memobase 服务是否正在运行")
        print("   2. 用户 ID 是否正确")
        print("   3. 用户是否有记忆数据")
        return 1

if __name__ == "__main__":
    sys.exit(main())

