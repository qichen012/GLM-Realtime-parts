#!/usr/bin/env python3
# coding: utf-8
"""
🚀 实时同步模块 - 方案3（混合模式）
===========================================
功能：
1. 异步队列：不阻塞对话流程
2. 状态追踪：每条记录都有 synced 状态
3. 自动重试：失败自动重试，有次数限制
4. 优雅降级：失败后由定时任务兜底
5. 完整日志：可追踪同步全过程

作者：AI Assistant
日期：2024-12
"""

import os
import sys
import json
import queue
import threading
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# 添加 memobase 到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMOBASE_PATH = os.path.join(PROJECT_ROOT, 'memobase')
if MEMOBASE_PATH not in sys.path:
    sys.path.insert(0, MEMOBASE_PATH)

from src.client.memobase.core.entry import MemoBaseClient
from src.client.memobase.core.blob import ChatBlob, BlobType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('RealtimeSync')


class MemobaseSyncWorker:
    """
    🧠 Memobase 实时同步工作类
    
    核心功能：
    - 异步队列处理对话同步
    - 失败自动重试（最多3次）
    - 状态追踪和日志记录
    - 优雅退出处理
    """
    
    def __init__(
        self, 
        user_id: str,
        api_key: str = "secret",
        memobase_url: str = "http://localhost:8019/",
        max_queue_size: int = 1000,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        初始化同步工作类
        
        Args:
            user_id: 用户ID
            api_key: Memobase API Key
            memobase_url: Memobase 服务地址
            max_queue_size: 队列最大容量
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.user_id = user_id
        self.api_key = api_key
        self.memobase_url = memobase_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 同步队列
        self.sync_queue = queue.Queue(maxsize=max_queue_size)
        
        # 运行状态
        self.running = False
        self.worker_thread = None
        
        # 统计信息
        self.stats = {
            'total_enqueued': 0,    # 总入队数
            'total_synced': 0,       # 成功同步数
            'total_failed': 0,       # 失败数
            'queue_full_drops': 0,   # 队列满丢弃数
        }
        
        # Memobase 客户端（延迟初始化）
        self.client = None
        self.user = None
        
        logger.info(f"🔧 初始化 MemobaseSyncWorker - User: {user_id}, Queue: {max_queue_size}")
    
    def _init_client(self) -> bool:
        """
        初始化 Memobase 客户端
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info(f"🔌 连接 Memobase: {self.memobase_url}")
            self.client = MemoBaseClient(
                api_key=self.api_key,
                project_url=self.memobase_url
            )
            
            # 健康检查
            if not self.client.ping():
                logger.error("❌ Memobase 健康检查失败")
                return False
            
            # 获取或创建用户
            try:
                self.user = self.client.get_user(self.user_id)
                logger.info(f"✅ 用户已存在: {self.user_id}")
            except Exception as e:
                if "404" in str(e).lower() or "not found" in str(e).lower():
                    logger.info(f"💡 用户不存在，创建新用户: {self.user_id}")
                    self.client.add_user(id=self.user_id, data={})
                    self.user = self.client.get_user(self.user_id)
                    logger.info(f"✅ 用户创建成功")
                else:
                    raise e
            
            logger.info("✅ Memobase 客户端初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ Memobase 客户端初始化失败: {e}")
            return False
    
    def start(self):
        """启动同步工作线程"""
        if self.running:
            logger.warning("⚠️ 同步工作线程已在运行")
            return
        
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            name="MemobaseSyncWorker",
            daemon=True
        )
        self.worker_thread.start()
        logger.info("🚀 同步工作线程已启动")
    
    def stop(self, timeout: float = 5.0):
        """
        停止同步工作线程
        
        Args:
            timeout: 等待队列清空的超时时间（秒）
        """
        if not self.running:
            return
        
        logger.info(f"🛑 正在停止同步工作线程...")
        self.running = False
        
        # 等待队列清空（最多等待 timeout 秒）
        start_time = time.time()
        while not self.sync_queue.empty() and (time.time() - start_time) < timeout:
            remaining = self.sync_queue.qsize()
            logger.info(f"⏳ 等待队列清空... 剩余 {remaining} 条")
            time.sleep(0.5)
        
        # 等待线程结束
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
        
        logger.info("✅ 同步工作线程已停止")
        self._print_stats()
    
    def enqueue(self, dialogue_data: Dict[str, Any]) -> bool:
        """
        将对话数据加入同步队列
        
        Args:
            dialogue_data: 对话数据（必须包含 messages 字段）
        
        Returns:
            bool: 是否成功加入队列
        """
        try:
            # 验证数据格式
            if not isinstance(dialogue_data, dict):
                logger.error(f"❌ 无效的对话数据格式: {type(dialogue_data)}")
                return False
            
            if 'messages' not in dialogue_data:
                logger.error("❌ 对话数据缺少 'messages' 字段")
                return False
            
            # 添加元数据
            if 'sync_metadata' not in dialogue_data:
                dialogue_data['sync_metadata'] = {
                    'enqueued_at': datetime.now().isoformat(),
                    'retry_count': 0
                }
            
            # 非阻塞式加入队列
            self.sync_queue.put_nowait(dialogue_data)
            self.stats['total_enqueued'] += 1
            
            queue_size = self.sync_queue.qsize()
            logger.debug(f"📥 已加入同步队列 (队列大小: {queue_size})")
            
            return True
            
        except queue.Full:
            self.stats['queue_full_drops'] += 1
            logger.warning(f"⚠️ 同步队列已满 (最大: {self.sync_queue.maxsize})，丢弃当前对话")
            return False
        except Exception as e:
            logger.error(f"❌ 加入队列时出错: {e}")
            return False
    
    def _worker_loop(self):
        """
        工作线程主循环
        """
        logger.info("🔄 进入同步工作循环")
        
        # 初始化客户端
        client_ready = self._init_client()
        if not client_ready:
            logger.error("❌ 客户端初始化失败，同步功能不可用（将由定时任务兜底）")
            # 不直接退出，继续运行但不处理
        
        while self.running:
            try:
                # 从队列获取数据（超时1秒，以便检查 running 状态）
                dialogue_data = self.sync_queue.get(timeout=1.0)
                
                # 如果客户端未就绪，跳过（由定时任务处理）
                if not client_ready:
                    logger.warning("⚠️ 客户端未就绪，跳过实时同步")
                    self.stats['total_failed'] += 1
                    continue
                
                # 尝试同步
                success = self._sync_to_memobase(dialogue_data)
                
                if success:
                    self.stats['total_synced'] += 1
                else:
                    self.stats['total_failed'] += 1
                
                self.sync_queue.task_done()
                
            except queue.Empty:
                # 队列为空，继续等待
                continue
            except Exception as e:
                logger.error(f"❌ 工作循环异常: {e}")
                time.sleep(1.0)  # 避免异常导致的忙循环
        
        logger.info("🏁 同步工作循环结束")
    
    def _sync_to_memobase(self, dialogue_data: Dict[str, Any]) -> bool:
        """
        同步对话到 Memobase
        
        Args:
            dialogue_data: 对话数据
        
        Returns:
            bool: 同步是否成功
        """
        metadata = dialogue_data.get('sync_metadata', {})
        retry_count = metadata.get('retry_count', 0)
        
        for attempt in range(self.max_retries):
            try:
                messages = dialogue_data['messages']
                
                # 创建 ChatBlob
                blob = ChatBlob(messages=messages)
                
                # 插入数据
                self.user.insert(blob)
                
                # 立即同步
                self.user.flush(BlobType.chat, sync=True)
                
                logger.info(f"✅ 对话同步成功 (消息数: {len(messages)})")
                return True
                
            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"⚠️ 同步失败 (尝试 {attempt + 1}/{self.max_retries}): {e}"
                )
                
                # 更新重试次数
                metadata['retry_count'] = retry_count
                
                if attempt < self.max_retries - 1:
                    # 延迟后重试
                    time.sleep(self.retry_delay)
                else:
                    # 重试次数用尽
                    logger.error(
                        f"❌ 同步失败，重试次数已用尽 ({self.max_retries} 次)"
                    )
                    return False
        
        return False
    
    def _print_stats(self):
        """打印统计信息"""
        logger.info("=" * 60)
        logger.info("📊 Memobase 实时同步统计")
        logger.info("-" * 60)
        logger.info(f"  总入队数:        {self.stats['total_enqueued']}")
        logger.info(f"  成功同步数:      {self.stats['total_synced']}")
        logger.info(f"  失败数:          {self.stats['total_failed']}")
        logger.info(f"  队列满丢弃数:    {self.stats['queue_full_drops']}")
        
        if self.stats['total_enqueued'] > 0:
            success_rate = (self.stats['total_synced'] / self.stats['total_enqueued']) * 100
            logger.info(f"  成功率:          {success_rate:.1f}%")
        
        logger.info("=" * 60)
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取统计信息
        
        Returns:
            dict: 统计数据
        """
        return self.stats.copy()


# ==================== 辅助函数 ====================

def create_sync_worker(
    user_id: str,
    api_key: Optional[str] = None,
    memobase_url: Optional[str] = None
) -> MemobaseSyncWorker:
    """
    创建并启动同步工作器（便捷函数）
    
    Args:
        user_id: 用户ID
        api_key: API Key（可选，默认从环境变量读取）
        memobase_url: Memobase URL（可选，默认从环境变量读取）
    
    Returns:
        MemobaseSyncWorker: 同步工作器实例
    """
    api_key = api_key or os.getenv("MEMOBASE_TOKEN", "secret")
    memobase_url = memobase_url or os.getenv("MEMOBASE_URL", "http://localhost:8019/")
    
    worker = MemobaseSyncWorker(
        user_id=user_id,
        api_key=api_key,
        memobase_url=memobase_url
    )
    
    worker.start()
    return worker


# ==================== 测试代码 ====================

if __name__ == "__main__":
    """
    测试实时同步功能
    """
    print("🧪 测试 Memobase 实时同步模块\n")
    
    TEST_USER_ID = "3f6c7b1a-9d2e-4f8a-b5c3-e1f2a3b4c5d6"
    
    # 创建工作器
    worker = create_sync_worker(TEST_USER_ID)
    
    # 模拟对话数据
    test_dialogue = {
        "messages": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！我是AI助手。"}
        ],
        "timestamp": datetime.now().isoformat()
    }
    
    print("📤 发送测试对话...")
    success = worker.enqueue(test_dialogue)
    
    if success:
        print("✅ 已加入队列")
    else:
        print("❌ 加入队列失败")
    
    # 等待处理
    print("\n⏳ 等待处理（3秒）...")
    time.sleep(3)
    
    # 停止工作器
    worker.stop()
    
    print("\n✅ 测试完成")

