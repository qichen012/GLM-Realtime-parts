#!/usr/bin/env python3
# coding: utf-8
"""
Memobase 记忆管理器
用于从 Memobase 获取用户记忆并提供给 GLM 和 Claude Code
"""

import os
import sys
from typing import Optional

# 添加 memobase 到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMOBASE_PATH = os.path.join(PROJECT_ROOT, 'memobase')
if MEMOBASE_PATH not in sys.path:
    sys.path.insert(0, MEMOBASE_PATH)

from src.client.memobase.core.entry import MemoBaseClient

# --- 配置 ---
ACCESS_TOKEN = os.getenv("MEMOBASE_ACCESS_TOKEN", "secret")
MEMOBASE_URL = os.getenv("MEMOBASE_URL", "http://localhost:8019/")
DEFAULT_USER_ID = "3f6c7b1a-9d2e-4f8a-b5c3-e1f2a3b4c5d6"
# --- 配置结束 ---


class MemoryManager:
    """Memobase 记忆管理器"""
    
    def __init__(self, access_token: str = ACCESS_TOKEN, memobase_url: str = MEMOBASE_URL):
        """
        初始化记忆管理器
        
        Args:
            access_token: Memobase API Token
            memobase_url: Memobase 服务地址
        """
        self.access_token = access_token
        self.memobase_url = memobase_url
        self._client = None
    
    @property
    def client(self) -> MemoBaseClient:
        """延迟初始化 Memobase 客户端"""
        if self._client is None:
            try:
                self._client = MemoBaseClient(
                    api_key=self.access_token, 
                    project_url=self.memobase_url
                )
                # 测试连接
                if not self._client.ping():
                    print("⚠️ Memobase healthcheck 失败")
            except Exception as e:
                print(f"⚠️ 创建 Memobase 客户端失败: {e}")
                self._client = None
        return self._client
    
    def get_user_context(self, user_id: str, max_token_size: int = 1000) -> str:
        """
        获取用户的记忆上下文
        
        Args:
            user_id: 用户 ID
            max_token_size: 最大 token 数量
            
        Returns:
            格式化的记忆上下文字符串
        """
        try:
            if not self.client:
                return ""
            
            user = self.client.get_user(user_id)
            context_str = user.context(max_token_size=max_token_size)
            
            print(f"🧠 成功获取用户记忆 (User ID: {user_id[:8]}...)")
            return context_str
            
        except Exception as e:
            print(f"⚠️ 获取用户记忆失败: {e}")
            return ""
    
    def get_user_profile_summary(self, user_id: str) -> str:
        """
        获取用户画像摘要（更简洁的版本）
        
        Args:
            user_id: 用户 ID
            
        Returns:
            用户画像摘要
        """
        try:
            if not self.client:
                return ""
            
            user = self.client.get_user(user_id)
            profiles = user.profile()
            
            if not profiles:
                return ""
            
            summary = "用户画像摘要：\n"
            for p in profiles[:10]:  # 只取前10条
                summary += f"- {p.topic}::{p.sub_topic}: {p.content}\n"
            
            return summary
            
        except Exception as e:
            print(f"⚠️ 获取用户画像失败: {e}")
            return ""
    
    def format_memory_for_prompt(self, user_id: str, include_full_context: bool = True) -> str:
        """
        格式化记忆用于 LLM prompt
        
        Args:
            user_id: 用户 ID
            include_full_context: 是否包含完整上下文
            
        Returns:
            格式化后的记忆文本
        """
        if include_full_context:
            context = self.get_user_context(user_id)
            if context:
                return f"\n# 📚 用户记忆\n{context}\n"
        else:
            summary = self.get_user_profile_summary(user_id)
            if summary:
                return f"\n# 📚 用户信息\n{summary}\n"
        
        return ""


# 创建全局记忆管理器实例
memory_manager = MemoryManager()


def get_user_memory(user_id: str = DEFAULT_USER_ID, max_token_size: int = 1000) -> str:
    """
    便捷函数：获取用户记忆上下文
    
    Args:
        user_id: 用户 ID
        max_token_size: 最大 token 数量
        
    Returns:
        格式化的记忆上下文字符串
    """
    return memory_manager.get_user_context(user_id, max_token_size)


def format_memory_for_glm(user_id: str = DEFAULT_USER_ID) -> str:
    """
    为 GLM-Realtime 格式化记忆
    
    Args:
        user_id: 用户 ID
        
    Returns:
        适合 GLM 的记忆格式
    """
    return memory_manager.format_memory_for_prompt(user_id, include_full_context=True)


def format_memory_for_claude(user_id: str = DEFAULT_USER_ID) -> str:
    """
    为 Claude Code 格式化记忆
    
    Args:
        user_id: 用户 ID
        
    Returns:
        适合 Claude Code 的记忆格式
    """
    return memory_manager.format_memory_for_prompt(user_id, include_full_context=True)


if __name__ == "__main__":
    # 测试记忆管理器
    print("=== 测试记忆管理器 ===\n")
    
    print("1. 获取完整上下文:")
    context = get_user_memory()
    if context:
        print(context[:500] + "..." if len(context) > 500 else context)
    else:
        print("  无记忆数据或连接失败")
    
    print("\n2. 获取用户画像摘要:")
    summary = memory_manager.get_user_profile_summary(DEFAULT_USER_ID)
    if summary:
        print(summary)
    else:
        print("  无画像数据")
    
    print("\n=== 测试完成 ===")

