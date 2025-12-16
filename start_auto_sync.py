#!/usr/bin/env python3
# coding: utf-8
"""
启动 Memobase 自动同步守护进程
从项目根目录运行
"""

import sys
import os

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# 添加 memobase 路径
MEMOBASE_PATH = os.path.join(PROJECT_ROOT, 'memobase')
if MEMOBASE_PATH not in sys.path:
    sys.path.insert(0, MEMOBASE_PATH)

if __name__ == "__main__":
    print("🚀 启动 Memobase 自动同步守护进程...")
    print("💡 提示: 按 Ctrl+C 可以优雅退出\n")
    
    # 导入并运行守护进程
    from memory.auto_sync_daemon import main
    main()

