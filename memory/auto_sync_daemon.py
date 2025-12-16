#!/usr/bin/env python3
# coding: utf-8
"""
🛡️ Memobase 容错备份守护进程（方案3）
============================================
职责：作为实时同步的备份，处理实时同步失败的对话

工作模式：
1. 定时扫描 JSONL 文件，找出 synced=False 的记录
2. 尝试重新同步这些记录
3. 成功后标记为 synced=True
4. 如果实时同步工作正常，这里几乎无工作量

角色定位：
- 主力同步：realtime_sync.py（实时，0延迟）
- 容错备份：auto_sync_daemon.py（定时，兜底保障）
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# 添加 memobase 到 Python 路径
MEMOBASE_PATH = os.path.join(PROJECT_ROOT, 'memobase')
if MEMOBASE_PATH not in sys.path:
    sys.path.insert(0, MEMOBASE_PATH)

from src.client.memobase.core.entry import MemoBaseClient
from src.client.memobase.core.blob import ChatBlob, BlobType
from memory.data_logger import DialogueLogger  # 🔑 使用新的 logger 类
import json
from requests.exceptions import ConnectionError

# --- 配置 ---
ACCESS_TOKEN = os.getenv("MEMOBASE_ACCESS_TOKEN", "secret")
MEMOBASE_URL = os.getenv("MEMOBASE_URL", "http://localhost:8019/")
JSONL_FILE_PATH = os.path.join(PROJECT_ROOT, "data/save_data.jsonl")
USER_ID = "3f6c7b1a-9d2e-4f8a-b5c3-e1f2a3b4c5d6"

# 🔑 方案3：降低同步间隔（因为实时同步是主力）
SYNC_INTERVAL = int(os.getenv("MEMOBASE_SYNC_INTERVAL", "300"))  # 300秒 = 5分钟

# 日志配置
LOG_FILE = os.path.join(PROJECT_ROOT, "data/auto_sync.log")
# --- 配置结束 ---


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MemobaseSyncDaemon:
    """
    🛡️ Memobase 容错备份守护进程（方案3）
    
    职责：处理实时同步失败的对话记录
    只同步 synced=False 的记录
    """
    
    def __init__(self):
        self.running = True
        self.client = None
        self.user = None
        self.last_sync_time = None
        self.total_synced = 0
        self.total_retried = 0  # 🔑 新增：重试次数统计
        
        # 🔑 创建 logger 实例，用于访问新方法
        self.logger_helper = DialogueLogger(filename=JSONL_FILE_PATH)
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """处理退出信号"""
        logger.info("📥 收到退出信号，正在优雅退出...")
        self.running = False
    
    def init_memobase(self):
        """初始化 Memobase 连接"""
        try:
            logger.info("🔌 正在连接 Memobase...")
            self.client = MemoBaseClient(api_key=ACCESS_TOKEN, project_url=MEMOBASE_URL)
            
            # 测试连接
            if not self.client.ping():
                logger.error("❌ Memobase healthcheck 失败")
                return False
            
            logger.info(f"✅ Memobase 连接成功: {MEMOBASE_URL}")
            
            # 获取或创建用户
            try:
                self.user = self.client.get_user(USER_ID)
                logger.info(f"✅ 用户已存在: {USER_ID[:20]}...")
            except Exception as e:
                if "404" in str(e).lower() or "not found" in str(e).lower():
                    logger.info(f"💡 用户不存在，正在创建: {USER_ID[:20]}...")
                    self.client.add_user(id=USER_ID, data={})
                    self.user = self.client.get_user(USER_ID)
                    logger.info("✅ 用户创建成功")
                else:
                    raise e
            
            return True
            
        except ConnectionError:
            logger.error(f"❌ 无法连接到 Memobase: {MEMOBASE_URL}")
            logger.error("   请确认服务已启动并且地址/端口正确")
            return False
        except Exception as e:
            logger.error(f"❌ 初始化 Memobase 失败: {e}")
            return False
    
    def sync_once(self):
        """
        🛡️ 方案3：容错备份同步
        
        只同步 synced=False 的记录（实时同步失败的记录）
        成功后标记为 synced=True
        """
        if not os.path.exists(JSONL_FILE_PATH):
            logger.debug(f"📂 对话文件不存在: {JSONL_FILE_PATH}")
            return 0
        
        # 🔑 方案3：使用新方法获取未同步的对话
        unsynced_dialogues = self.logger_helper.get_unsynced_dialogues()
        
        if not unsynced_dialogues:
            logger.debug("✓ 扫描完成: 所有对话已同步")
            return 0
        
        logger.info(f"🔍 发现 {len(unsynced_dialogues)} 条未同步对话，开始处理...")
        
        inserted_count = 0
        failed_count = 0
        
        for line_no, dialogue_data in unsynced_dialogues:
            try:
                messages = dialogue_data.get("messages")
                retry_count = dialogue_data.get("retry_count", 0)
                
                if not messages or not isinstance(messages, list):
                    logger.warning(f"⚠️ 第 {line_no} 行格式不正确，跳过")
                    failed_count += 1
                    continue
                
                # 🔑 检查重试次数（避免无限重试）
                MAX_RETRIES = 5
                if retry_count >= MAX_RETRIES:
                    logger.warning(f"⚠️ 第 {line_no} 行重试次数已达上限 ({MAX_RETRIES})，跳过")
                    failed_count += 1
                    continue
                
                # 插入到 Memobase
                blob = ChatBlob(messages=messages)
                self.user.insert(blob)
                self.user.flush(BlobType.chat, sync=True)
                
                # 🔑 方案3：同步成功，标记为 synced=True
                self.logger_helper.update_sync_status(line_no, synced=True)
                
                inserted_count += 1
                self.total_synced += 1
                self.total_retried += 1
                logger.info(f"  ✓ 第 {line_no} 行重试成功 (含 {len(messages)} 条消息)")
                
            except Exception as e_insert:
                logger.error(f"⚠️ 第 {line_no} 行重试失败: {e_insert}")
                failed_count += 1
                
                # 🔑 增加重试计数（但不标记为 synced）
                dialogue_data['retry_count'] = retry_count + 1
        
        # 打印结果
        if inserted_count > 0:
            logger.info(f"✅ 容错同步完成: 成功 {inserted_count} 条，失败 {failed_count} 条")
        elif failed_count > 0:
            logger.warning(f"⚠️ 容错同步完成: 失败 {failed_count} 条")
        else:
            logger.debug("✓ 容错同步完成: 无需处理")
        
        return inserted_count
    
    def run(self):
        """运行守护进程"""
        logger.info("="*60)
        logger.info("🛡️ Memobase 容错备份守护进程启动（方案3）")
        logger.info("="*60)
        logger.info("💡 工作模式: 容错备份（处理实时同步失败的记录）")
        logger.info(f"📂 对话文件: {JSONL_FILE_PATH}")
        logger.info(f"🔄 扫描间隔: {SYNC_INTERVAL} 秒 ({SYNC_INTERVAL//60} 分钟)")
        logger.info(f"📝 日志文件: {LOG_FILE}")
        logger.info(f"👤 用户 ID: {USER_ID[:20]}...")
        logger.info("="*60)
        logger.info("\n📊 职责说明:")
        logger.info("   • 主力同步: realtime_sync.py (实时，0延迟)")
        logger.info("   • 容错备份: auto_sync_daemon.py (定时，兜底保障)")
        logger.info("   • 只处理 synced=False 的记录")
        logger.info("="*60)
        
        # 初始化 Memobase
        if not self.init_memobase():
            logger.error("❌ 无法初始化 Memobase，退出")
            return
        
        logger.info("\n✅ 守护进程运行中... (按 Ctrl+C 退出)")
        logger.info(f"💡 提示: 每 {SYNC_INTERVAL//60} 分钟扫描一次未同步记录\n")
        
        # 首次立即同步
        self.last_sync_time = datetime.now()
        self.sync_once()
        
        # 主循环
        while self.running:
            try:
                time.sleep(10)  # 每10秒检查一次
                
                # 检查是否到了同步时间
                elapsed = (datetime.now() - self.last_sync_time).total_seconds()
                if elapsed >= SYNC_INTERVAL:
                    logger.info(f"⏰ 定时扫描触发 ({elapsed:.0f}秒)")
                    self.sync_once()
                    self.last_sync_time = datetime.now()
                
            except Exception as e:
                logger.error(f"❌ 主循环错误: {e}")
                time.sleep(60)  # 出错后等待1分钟再继续
        
        # 退出前最后同步一次
        logger.info("📥 退出前执行最后一次扫描...")
        self.sync_once()
        
        logger.info("="*60)
        logger.info(f"👋 守护进程已退出")
        logger.info(f"   • 总共同步: {self.total_synced} 条对话")
        logger.info(f"   • 容错重试: {self.total_retried} 条对话")
        logger.info("="*60)


def main():
    """主函数"""
    daemon = MemobaseSyncDaemon()
    daemon.run()


if __name__ == "__main__":
    main()

